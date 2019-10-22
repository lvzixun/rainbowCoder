## lua5.3.5 gc实现

之前对lua的gc实现只是了解个大概，多数是在遇到问题的时候看特定的gc代码。对于细节实现并没有花时间认真查看，最近由于工作上的一些原因需要协助其他童鞋对gc做一定的优化，所以决定花时间认真阅读了lua 5.3.4版本的gc实现，感觉还是收获挺多的，之前不了解的地方也豁然开朗了，对lua 整个gc的工作流程又熟悉了几分。 
于是就想把之前丢掉的blog给从新拿起来，记录下自己这两天的一些收获和见解。 ;D

----

所有脱离了语言特性和应用环境而去谈论gc的实现和方法都是在耍流氓。gc是对语言内部对象的管理；语言特性不同，选择的策略不同。虽然同样都是用标记清除，但是实现的复杂度和难度确相差甚远。对于lua gc来说因为`weak table`,`__gc`元方法还有分步的策略选择，让简单的标记回收的实现复杂度上升好几个数量级。

### 标记回收
lua使用的是mark-sweep(标记回收)的方式来实现gc的。 对于整个系统中被gc管理的对象有: `proto`,`closure`, `table`,`coroutine`, `userdata`, `string`(分为`short string`和`long string`)。这些对象在被创建的那一时刻会被link到全局唯一`struct global_State`中的`allgc`这个链表上面。 
GC整个过程简单来说：首先是mark阶段，mark时会从整个state的root节点开始遍历标记。每个对象被标记时会有三种状态, `white`, `black`和`gray`:

| status | description |
|:---:|:------:|
|`white`|未被引用|
|`black`|被引用;且本身本身没有包含未处理的引用|
|`gray` | 被引用，但是本身包含为处理的引用，需要遍历对象本身做进一步的mark|

经过多次的`luaC_step`之后， 会将整个vm中的`GCobject`全部正确标记。 之后进入sweep阶段，对所有的`white`的对象做sweep清理操作；再之后对有`__gc`方法的对象去执行相应的`__gc`方法。

----
对于默认的lua gc是通过分配内存来进行驱动gc的工作。 当在整个lua vm中没有内存产生分配，自然gc也不会进行工作。 当有内存分配时，对于gc一次step工作量的多少是根据在`struct global_State`中`GCdebt`(债务)来决定的。 lua的每次内存分配和释放都是通过`void *luaM_realloc_ (lua_State *L, void *block, size_t osize, size_t nsize)` 这个函数来实现，在`luaM_realloc_`函数中每次内存的变化都会加到`GCdebt`上面: 
~~~.c
g->GCdebt = (g->GCdebt + nsize) - realosize;
~~~
`GCdebt`的多少决定了调用一次`luaC_step`所做的gc工作量。 对GC速度和间隔的控制，全部都是通过`GCdebt`的大小来实现的。 


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

`luaC_step`函数是lua 默认gc的唯一入口，每次调用执行lua gc工作至少一步，函数实现如下： 
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

整个阶段从1-8，除了`GCSatomic`阶段外，其他的阶段都是可以分步执行的。经过整个一个gc循环后，会再被设置为`GCSpause`状态，等待下一次的gc step。 每个阶段的执行都会返回一个工作执行了多少，表示当前`singlestep`执行了多少工作量，从而控制是否执行下一次的`singlestep`。
~~~.c
  do {  /* repeat until pause or enough "credit" (negative debt) */
    lu_mem work = singlestep(L);  /* perform one single step */
    debt -= work;
  } while (debt > -GCSTEPSIZE && g->gcstate != GCSpause);
~~~

#### GCSpropagate

`GCSpropagate`从root节点开始逐个mark对象，mark的过程就是在不停的遍历`gray`链表，拿到一个对象之后调用`propagatemark`函数，对不同的类型调用相应的`travers*`方法来进行mark：不断的将对象标记成`gray`颜色，加入`gray`链表。

对于一个table对象`{[1] = {}, [2] = {}}`当从其他对象标记到该table的时候，会将该对象标记为`gray`，同时加入`gray`链表中，之后经过下一次的`propagatemark`，将该table标记为`black`同时取出`table1`和`table2`放入`gray`链表中。之后继续遍历`gray`链表，直到
链表里面不再有对象。 这个过程很像传播，所以取名叫`propagate`, 在此阶段对`weaktable`做了一些处理。将`__mode='k'`的对象会放入`ephemeron`的链表中，`__mode='v'`的对象会放入`weak`链表。 `__mode='kv'`的对象会放入`allweak`链表中；之后等待在atomic阶段被处理。

因为该阶段是可以分步执行，所以就会遇到之前已经标记为`black`的对象，再次被人修改，加入了新的pair。所以这里就需要处理标记，例如：对于已经标记成黑色的`t = {}`对象，设置`t.key = {}`
时会调用`luaC_barrierback`将`t`标记为`gray`同时放入`grayagain`链表中。
然而，对于`mt = {}; setmetatable(t, mt)`的行为，却调用的是`luaC_barrier`，将设置的mt对象标记`gray`，放入`gray`链表中等待下次被标记。

----

对于衡量标记阶段的工作量，是根据标记对象的真实大小来衡量的。 每次执行`singlestep`函数返回的`work`工作量是标记了多少对象的总内存(并非是真实的释放了`work`大小的内存)。`work`会反应到`dedt`上，来决定下一次的`singlestep`是不是要执行。


#### GCSatomic

原子阶段的实现在函数`static l_mem atomic (lua_State *L)`中，此阶段是不可分割的，不能分步处理。处理流程如下：

* 1 在atmoic阶段中会将会先执行`propagateall(g);`将vm中还未标记的对象全部标记。之后开始标记`grayagain`链表中的全部对象；
* 2 遍历清理存储`weaktable`的`ephemeron`, `allweak`, `weak`三个链表的`key`和`value`; 
* 3 将当前不再存活但是拥有`__gc`方法的对象从`finobj`链表插入到`tobefnz`链表中，等待复活执行`__gc`元方法。 

此阶段还有个细节是会执行`g->currentwhite = cast_byte(otherwhite(g));  /* flip current white */` 将当前的白色做flip，之所以用另外个值来标记`white`对象，是因为sweep阶段可以分步，有可能在sweep状态中，会执行创建一个新的对象挂接到`allgc`或者`finobj`链表上, 如果把这个对象标记成`black`，那就有可能再也没机会被变回`white`，所以此处加了一个新`white`来区分之前标记的`white`对象, 同时避免被清理。
atomic阶段最后会调用`entersweep`函数，将`sweep`指针设置为`allgc`,进入sweep阶段。

----
因为此阶段是不能分步执行，所以在此阶段对gc卡顿的影响是最大。此阶段会遍历整个vm中所有的`weaktable`，以及带有`__gc`元方法的对象。如果系统大量存在这两种对象的话， 会导致atomic工作量增加，从而造成像stop world那样的卡顿。
此阶段的工作量，依然是根据标记对象的大小来衡量。


#### GCSswpallgc, GCSswpfinobj, GCSswptobefnz和GCSswpend
前三个阶段是清理阶段，分别对应了清理链表`allgc`, `finobj`和`tobefnz`上面标记为`当前white`的对象。清理的过程也很简单，就是遍历链表上面的对象，是`otherwhite`才会被清理掉(因为在atomic阶段已经将`currentwhite`做了flip)，其他颜色的对象会设置成`white`，等待下一次gc循环的标记处理。

由于lua对short string做了intern处理。同样的short string在vm中只会存在唯一的一个string对象，所有的short string都被放在`stringtable strt;`这个hash表中。所以在GCSswpend阶段会resize strt。

----
此阶段可以分步执行，每次`singlestep` 执行`GCSWEEPMAX`个对象，工作量是根据每个对象的估算值`GCSWEEPCOST`相乘的出，对于估算为什么不像mark阶段用对象的真实大小来衡量工作量, 此处有询问云风，给出的解释是:
>1. mark 和 sweep 总要有一边去按内存数量来累加，这样才能匹配上分配的数字。
 2. mark 需要访问的 gcobject 的数量 一定 少于 sweep 需要处理的 gcobject 数量。所以，让 sweep 跑的快一点比较好。

mark一个对象，需要遍历这个对象的所有子对象，但是sweep阶段的free确不需要，相比来说用`GCSWEEPCOST`来衡量会更合适。


#### GCScallfin 
这个阶段是遍历`tobefnz`链表，执行被复活的对象 `__gc`元方法，每执行完一个对象，就把改对象打上`FINALIZEDBIT`标记，表示已经执行过`__gc`元方法，避免此对象如果被`__gc`元方法中复活再失去引用时被重复调用`__gc`元方法；同时把对象从`tobefnz`链表移除，插入到`allgc`链表中，等待下次gc被清理。
此阶段是可以被分步执行，每一次的工作量是有`gcfinnum`字段来控制。跟sweep阶段固定每次都清理`GCSWEEPMAX`个对象不同，`gcfinnum`的增长是每次都翻倍的。实现代码如下:
~~~.c
/*
** call a few (up to 'g->gcfinnum') finalizers
*/
static int runafewfinalizers (lua_State *L) {
  global_State *g = G(L);
  unsigned int i;
  lua_assert(!g->tobefnz || g->gcfinnum > 0);
  for (i = 0; g->tobefnz && i < g->gcfinnum; i++)
    GCTM(L, 1);  /* call one finalizer */
  g->gcfinnum = (!g->tobefnz) ? 0  /* nothing more to finalize? */
                    : g->gcfinnum * 2;  /* else call a few more next time */
  return i;
}
~~~

-----
所有带有`__gc`元方法的对象，都会被保留到下一次gc循环才会被真正回收。GCScallfin阶段的工作量与sweep一致，都是用估算的对象大小`GCFINALIZECOST`来衡量。 当`tobefnz`链表为空，则表示GCScallfin阶段结束，同时切换状态到最初的GCSpause阶段，进入下一次的gc循环。


### `global_State`中的`GCObject`链表
lua vm中的`GCObject`对象，当前时刻只会存在以下链表中的其中一个。

* 1 `allgc`  每创建一个新的`GCObject`对象，都会被挂接到`allgc`上面，记录了全部被gc管理的对象。
* 2  `finobj` 当对一个对象设置`__gc`元方法时，会将改对象从`allgc`移入到`finobj`，因为是单项链表的原因，这个查找移入是O(n)的时间开销。因为每次创建`GCObject`必然都是在`allgc`的head，查找遍历很快；所以对于创建一个新对象应当尽可能的立即设置`__gc`元方法。
* 3  `gray`  在mark阶段用来传播标记用的链表。
* 4  `grayagain`  在mark阶段对于已经标记为`black`的对象再次修改，将会把对象放入`grayagain`链表中，在atomic阶段一次性处理完，从而避免反复进入`gray`链表进行标记遍历。
* 5  `weak`  记录元表中`__mode='v'`的weaktable。
* 6  `ephemeron` 记录元表中`__mode='k'`的weaktable。
* 7  `allweak`  记录元表中`__mode='kv'`的weaktable。
* 8 `tobefnz` 记录将要执行`__gc`元方法的对象。
* 9 `fixedgc` 用来记录不需要被gc回收的对象。





