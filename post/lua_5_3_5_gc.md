## lua5.3.5 gc实现

之前对lua的gc实现只是了解个大概，多数是在遇到问题的时候看特定的gc代码。对于细节实现并没有花时间认真查看，最近由于工作上的一些原因需要协助其他童鞋对gc做一定的优化，所以决定花时间认真阅读了lua 5.3.4版本的gc实现，感觉还是收获挺多的，之前不了解的地方也豁然开朗了，对lua 整个gc的工作流程又熟悉了几分。 
于是就想把之前丢掉的blog给从新拿起来，记录下自己这两天的一些收获和见解。 ;D

----

所有脱离了语言特性和应用环境而去谈论gc的实现和方法都是在耍流氓。gc是对语言内部对象的管理；语言特性不同，选择的策略不同。虽然同样都是用标记清除，但是实现的复杂度和难度确相差甚远。对于lua gc来说因为`weak table`,`__gc`元方法还有分步的策略选择，让简单的标记回收的实现复杂度上升好几个数量级。

### 标记回收
lua使用的是mark-sweep(标记回收)的方式来实现gc的。 对于整个系统中被gc管理的对象有: `proto`,`closure`, `table`,`coroutine`, `userdata`, `string`(分为`short string`和`long string`)。这些对象在被创建的那一时刻会被link到全局唯一`struct global_State`中的`allgc`这个双向链表上面。 
GC整个过程简单来说：首先是mark阶段，mark时会从整个state的根节点开始遍历标记。每个对象被标记时会有三种状态, `white`, `black`和`gray`。 `white`未被引用;`black`被引用;且本身本身没有包含未处理的引用;`gray`被引用，但是本身包含为处理的引用，需要遍历对象本身做进一步的mark。经过多次的`luaC_step`之后， 会将整个vm中的gcobject全部正确标记。 之后进入sweep阶段，对所有的`white`的对象做sweep清理操作。再之后对有`__gc`方法的对象去执行相应的`__gc`方法。

----
对于默认的lua gc是通过分配内存来进行驱动gc的工作。 当在整个lua vm中没有内存产生分配，自然gc也不会进行工作。 当有内存分配时，对于gc一次step工作量的多少是根据在`struct global_State`中`GCdebt`(债务)来决定的。 lua的每次内存分配和释放都是通过`void *luaM_realloc_ (lua_State *L, void *block, size_t osize, size_t nsize)` 这个函数来实现，在`luaM_realloc_`函数中每次内存的变化都会加到`GCdebt`上面: `g->GCdebt = (g->GCdebt + nsize) - realosize;`  `GCdebt`的多少决定了调用一次`luaC_step`所做的gc工作量。 对GC速度和间隔的控制，全部都是通过`GCdebt`的大小来实现的。 


当调用lua函数`collectgrabage` ["setstepmul"](https://www.lua.org/manual/5.3/manual.html#pdf-collectgarbage)设置只是`global_State`中的`gcstepmul`，作用是把当前的`GCdebt`乘以`gcstepmul`这个系数，将债务放大(在函数`static l_mem getdebt (global_State *g)`中实现)；

~~~.c
/*
** get GC debt and convert it from Kb to 'work units' (avoid zero debt
** and overflows)
*/
static l_mem getdebt (global_State *g) {
  l_mem debt = g->GCdebt;
  int stepmul = g->gcstepmul;
  if (debt <= 0) return 0;  /* minimal debt */
  else {
    debt = (debt / STEPMULADJ) + 1;
    debt = (debt < MAX_LMEM / stepmul) ? debt * stepmul : MAX_LMEM;
    return debt;
  }
}
~~~

["setpause"](https://www.lua.org/manual/5.3/manual.html#pdf-collectgarbage)设置的也只是`gcpause`字段，当每次GC执行完一轮的时候，会统计出当前系统中还剩多少内存，之后乘以`gcpause`这个系数(默认200)，将`GCdebt`设置成`debt = gettotalbytes(g) - threshold;`根据默认系数这个值多数为`-threshold/2`；因为所有触发gc是在对象创建时主动调用`luaC_condGC`来触发的。 

~~~.c
#define luaC_condGC(L,pre,pos) \
	{ if (G(L)->GCdebt > 0) { pre; luaC_step(L); pos;}; \
	  condchangemem(L,pre,pos); }
~~~

每次在执行gc step时都会判断GCdebt是否大于0，所以在下一次gc循环开启前，就必须要分配足够多的内存来将`GCdebt`变为大于0的值来触发下一轮的GC。


----

~~~.c

/*
** performs a basic GC step when collector is running
*/
void luaC_step (lua_State *L) {
  global_State *g = G(L);
  l_mem debt = getdebt(g);  /* GC deficit (be paid now) */
  if (!g->gcrunning) {  /* not running? */
    luaE_setdebt(g, -GCSTEPSIZE * 10);  /* avoid being called too often */
    return;
  }
  do {  /* repeat until pause or enough "credit" (negative debt) */
    lu_mem work = singlestep(L);  /* perform one single step */
    debt -= work;
  } while (debt > -GCSTEPSIZE && g->gcstate != GCSpause);
  if (g->gcstate == GCSpause)
    setpause(g);  /* pause until next cycle */
  else {
    debt = (debt / g->gcstepmul) * STEPMULADJ;  /* convert 'work units' to Kb */
    luaE_setdebt(g, debt);
    runafewfinalizers(L);
  }
}
~~~