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
通过`GCdebt` 这一个参数来控制gc的执行间歇率和步进倍率，我觉得这是很巧妙的设计。

----

`luaC_step`函数是lua 默认gc的唯一入口，每次调用执行lua gc工作一步或者多步,函数实现如下： 
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

### gc step

lua gc 分为以下阶段:

| 阶段顺序 | 阶段名称 | 阶段执行逻辑 | 是否可以分步执行 |
|:---:|:----:|:------:|:----:|
| 1 | GCSpause | gc暂停阶段 | yes |
| 2 | GCSpropagate | gc标记传播阶段 | yes |
| 3 | GCSatomic | 原子标记处理阶段 | no |
| 4 | GCSswpallgc | 清理在`allgc`链表上面标记为white的对象 | yes |
| 5 | GCSswpfinobj | 清理`finobj`链表上面标记为white的对象 | yes |
| 6 | GCSswptobefnz | 清理`tobefnz`链表上面标记为white的对象 | yes |
| 7 | GCSswpend | 结束清理阶段,准备进入调用gc元方法阶段 | - |
| 8 | GCScallfin | 执行有`__gc`元方法的对象 | yes |

整个阶段从1-8，除了`GCSatomic`阶段外，其他的阶段都是可以分步执行的。经过整个一个gc循环后，会再被设置为`GCSpause`状态，等待下一次的gc step。 每个阶段的执行都会返回一个工作执行了多少，表示当前singlestep执行了多少工作量，从而控制是否执行下一次的singlestep.
~~~.c
  do {  /* repeat until pause or enough "credit" (negative debt) */
    lu_mem work = singlestep(L);  /* perform one single step */
    debt -= work;
  } while (debt > -GCSTEPSIZE && g->gcstate != GCSpause);
~~~

#### GCSpropagate

`GCSpropagate`从root节点开始逐个mark对象，mark的过程就是在不停的遍历`gray`链表，拿到一个对象之后调用`propagatemark`函数，对不同的类型调用相应的`travers*`方法来进行mark调用`reallymarkobject`方法，不断的将对象标记成`gray`颜色，加入`gray`链表。对于一个table对象`{[1] = {}, [2] = {}}`当从其他对象标记到改table的时候，会将该对象标记为`gray`，同时加入`gray`链表中，之后经过下一次的`propagatemark`，将改table标记为`black`同时取出table1和table2放入`gray`链表中。之后继续遍历`gray`链表，直到
链表里面不再有对象。 这个过程很像传播，所以取名叫`Spropagate`, 再此阶段对weaktable的对象做了一些处理。将`__mode='k'`的对象会放入`ephemeron`的链表中，`__mode='v'`的对象会放入`weak`链表。 `__mode='kv'`的对象会放入`allweak`链表中。之后等待在atomic阶段被处理。



因为该阶段是可以分步执行，所以就会遇到之前已经标记为`black`的对象，再次被人修改，加入了新的pair对象。所以这里就需要处理标记，例如：对于已经标记成黑色的`t = {}`对象，设置`t.key = {}`
时会调用`luaC_barrierback`将t标记为`gray`同时放入`grayagain`链表中，在atomic阶段再次被遍历标记。
然而，对于`mt = {}; setmetatable(t, mt)`的行为，却调用的是`luaC_barrier`，将设置的mt对象标记`gray`，放入`gray`链表中等待下次被标记。

----

对于衡量标记阶段的工作量，是根据标记对象的真实大小来衡量的。 每次执行`singlestep`函数返回的`work`工作量是标记了多少对象的总内存(并非是真实的释放了`work`大小的内存)。`work`会反应到`dedt`上，来决定下一次的`singlestep`是不是要执行。


#### GCSatomic

原子阶段的实现在函数`static l_mem atomic (lua_State *L)`中，此阶段是不可分割的，不能分步处理。在atmoic阶段中会将会先执行`propagateall(g);`将vm中还未标记的对象全部标记。之后开始标记`grayagain`链表中的全部对象；之后遍历清理存储weak table的`ephemeron`, `allweak`, `weak`三个链表的key和value。 将当前不再存活但是拥有`__gc`方法的对象从`finobj`链表插入到`tobefnz`链表中，等待复活执行`__gc`元方法。 此阶段还有个细节是会执行`g->currentwhite = cast_byte(otherwhite(g));  /* flip current white */` 将当前的白色做flip，之所以用另外个值来标记white对象，是因为sweep阶段可以分步，有可能在sweep状态中，会执行创建一个新的对象挂接到`allgc`, 如果把这个对象标记成black，那就有可能再也没机会被变回white，所以此处加了一个新white来区分之前标记的white对象, 同时避免被清理。
atomic阶段最后会调用`entersweep`函数，将`sweep`指针设置为`allgc`,进入sweep阶段。

----
因为此阶段是不能分步执行，所以在此阶段对gc卡顿的影响是最大。此阶段会遍历整个vm中所有的weak table，以及带有`__gc`元方法的对象。如果系统大量存在这两种对象的话， 会导致atomic工作量增加，从而造成像stop world那样的卡顿。
此阶段的工作量，依然是根据标记对象的大小来衡量。


#### GCSswpallgc, GCSswpfinobj, GCSswptobefnz
这三个阶段是清理阶段，分别对应了清理链表`allgc`, `finobj`和`tobefnz`上面标记为当前white的对象。
