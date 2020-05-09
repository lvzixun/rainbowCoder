## lua5.4 gc实现

近期因为lua5.4 更新了rc1，同时云风将其合并到了skynet的master上面，所以花时间了解了下新版本的gc实现。于是着手写一篇blog记录了下，这两天对lua分代gc的了解。
相比于之前的5.3的分步gc实现，在5.4多了新的分代gc。而且这两种gc工作模式可以通过`lua_gc`api来进行相互切换。
在之前的[这篇blog](https://rainbowcoder.com/lua_5_3_5_gc.html)中有详细记录之前5.3分步gc的实现，再次不在多说，主要记录下新增的分代gc的实现。

-----

原来在`GCObject`中的用来标记当前颜色和状态的`marked`的低3个bit用来存储对象的age值。在分代gc模式下，所有的对象都会对应一个age值，来表示当前对象已经存活的时间和状态。
对于分代gc来说，回收分为`minor collection`(次收集回收)和`major collection`(主收集回收)两种方式。分代gc是基于如下假设来运行的：对于一个正常的系统中的对象，随着
运行时间的增加，总是会趋于一个稳定的大小，被回收的对象多数在新生对象中产生。所以对于分代gc来说，主要去对新生对象集合做gc收集，同时在必要的时候对系统中的所有对象做个主收集回收
。这样的好处是临时对象能够尽快的被释放，同时减少了mark和sweep的数目。这样相比于增量gc的好处是，内存可以及时的被释放，同时减少因为gc触发而导致的内存波动。

### gen mode
gc工作的入口依然是`void luaC_step (lua_State *L)`函数，但是此函数的实现加了对当前gc工作模式的判断，来选择是进行`gen mode`(分代模式) 还是`inc mode`增量模式。
对于`gen mode`的入口是`static void genstep (lua_State *L, global_State *g)` 函数。`genstep`函数会根据当前的内存量，来选择是做次收集回收还是主收集回收。
~~~.lua
static void genstep (lua_State *L, global_State *g) {
  if (g->lastatomic != 0)  /* last collection was a bad one? */
    stepgenfull(L, g);  /* do a full step */
  else {
    lu_mem majorbase = g->GCestimate;  /* memory after last major collection */
    lu_mem majorinc = (majorbase / 100) * getgcparam(g->genmajormul);
    if (g->GCdebt > 0 && gettotalbytes(g) > majorbase + majorinc) {
      lu_mem numobjs = fullgen(L, g);  /* do a major collection */
      if (gettotalbytes(g) < majorbase + (majorinc / 2)) {
        /* collected at least half of memory growth since last major
           collection; keep doing minor collections */
        setminordebt(g);
      }
      else {  /* bad collection */
        g->lastatomic = numobjs;  /* signal that last collection was bad */
        setpause(g);  /* do a long wait for next (major) collection */
      }
    }
    else {  /* regular case; do a minor collection */
      youngcollection(L, g);
      setminordebt(g);
      g->GCestimate = majorbase;  /* preserve base value */
    }
  }
  lua_assert(isdecGCmodegen(g));
}
~~~
`genmajormul`字段是通过之前的`collectgarbage("generational", minormul, majormul)`函数设置的。这个值是个百分比，表示当前内存超过了上一次主收集回收时的内存的`genmajormul%`时
触发下一次的主收集回收。反之将会进入次级回收 `youngcollection`中；在分代gc的策略中`youngcollection`应该是经常被触发，`fullgen`被触发的时机已经是极少。多数的对象都会在 `youngcollection`中被回收掉了。
就算是触发了`fullgen`也应该会很快。 `genmajormul`这个值默认是100,  在lgc.h有如下定义:
~~~.c
/* Default Values for GC parameters */
#define LUAI_GENMAJORMUL         100
#define LUAI_GENMINORMUL         20
~~~
100代表的意思是内存相比于上一次主收集回收时的内存翻倍情况下再次触发主收集。 当第一次触发会尝试做一次`fullgen`主收集，主收集之后会再次判断新增的内存是否有降低到一半，如果降低到一半将会设置`setminordebt`
下次次级回收的时机，从而继续进行次级回收。如果`fullgen`执行之后仍然大于新增内存的一半，将会`setpause`下次gc启动将会进入主收集回收`stepfull`。 在`stepfull`中会进行判断新增的对象个数是否有超过上一次的`lastatomic`对象个数的
`1/8`，如果超过了认为是进入了`bad collection`直接切换到`inc mode`模式做`stop world`的sweep。对于`fullgen`主收集回收来说，全部都是切换到`inc mode`同时`stop world`的方式来做回收的。此时有个问题是，如果
当前vm中在不停的分配和持有object，将会导致`gen mode`模式不停的进入`bad collection`状态，然而这个状态会`stop world`的mark和sweep整个vm的object。在应用层看来会定时的卡顿。不过每次`bad collection`的回收完之后
会进行调用`setpause(g);`如果vm在不停的增长内存的话， 下次启动的间隔也会变长。所以并不会太频繁的触发`bad collection`，但是因为`stop world`的原因，所以一旦多次触发主收集回收的话，很大概率会导致vm的卡顿。

### youngcollection
对于一个正常的vm来说，次级回收应该是被多数情况下触发的。次级回收的入口是在`static void youngcollection (lua_State *L, global_State *g)` 函数。整个次级回收会根据`allgc`, `survival`, `old`, `reallyold`
这几个链表(同理对于带有`__gc`元方法的对象会放在`finobjsur`, `finobjold`, `finobjrold`链表中，在此只说明下不带元表的正常对象) 和 每个对象的`age`字段来进行做sweep。任意一个可回收的对象的age只会分为如下的状态:
~~~.c
/* object age in generational mode */
#define G_NEW       0   /* created in current cycle */
#define G_SURVIVAL  1   /* created in previous cycle */
#define G_OLD0      2   /* marked old by frw. barrier in this cycle */
#define G_OLD1      3   /* first full cycle as old */
#define G_OLD       4   /* really old object (not to be visited) */
#define G_TOUCHED1  5   /* old object touched this cycle */
#define G_TOUCHED2  6   /* old object touched in previous cycle */
~~~

对于一个正常的对象，在经历了多次的gc循环之后会经过 如下状态的转换:
```
G_NEW -> G_SURVIVAL -> G_OLD1 -> G_OLD
```




