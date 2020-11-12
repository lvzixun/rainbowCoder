## lua-5.4.2 stacksize产生的bug

上周[杰涛童鞋](https://github.com/t0350)遇到一个很奇怪的问题：在特定情况下元表重载`__add`运算符会导致返回结果为`nil`, 经过漫长的定位和排查之后发现是skynet用的lua内部产生的bug。Orz
 因为skynet master分支用的[lua](https://github.com/lua/lua)很新，是lua5.4.2。这个版本还没有发布release，roberto最新的提交也是在半个月前。知道原因后，可以构造如下的简单测试用例复现:

~~~.lua
local t = {}
setmetatable(t, t)
function t.__add(a, b)
    t[a] = b
    return t[a]
end

local a = 1
local b = 2
local c = 3
local d = 4
local e = 5
local a = 1
local b = 2
local c = 3
local d = 4
local e = 5
local a = 1
local b = 2
local c = 3
local d = 4
local e = 5
local a = 1
local b = 2
local b = 3
local d = 4
local e = 5
local a = 1
local b = 2
local b = 3
local a = 1
local b = 2
local b = 3
local b = 3
local c= t+2
print(c) -- nil，expect 2
~~~
出现此bug的原因是，每个`lua_State`在进行分配`stack`的时候，都会额外分配`EXTRA_STACK`长度的slot，这些slot是专为元方法使用的额外空间，减少元方法在触发时还要检查`stack`是否grow。在触发元方法时会调用`luaT_callTMres`函数，这个函数的实现如下:
~~~.c
void luaT_callTMres (lua_State *L, const TValue *f, const TValue *p1,
                     const TValue *p2, StkId res) {
  ptrdiff_t result = savestack(L, res);
  StkId func = L->top;
  setobj2s(L, func, f);  /* push function (assume EXTRA_STACK) */
  setobj2s(L, func + 1, p1);  /* 1st argument */
  setobj2s(L, func + 2, p2);  /* 2nd argument */
  L->top += 3;
  /* metamethod may yield only when called from Lua code */
  if (isLuacode(L->ci))
    luaD_call(L, func, 1);
  else
    luaD_callnoyield(L, func, 1);
  res = restorestack(L, result);
  setobjs2s(L, res, --L->top);  /* move result to its place */
}
~~~
在调用之初会对func元方法填充参数，这里并没有判断`stack`是否足够，因为假设了`stack`必然会有`EXTRA_STACK`长度的空间供填充数据。因此这里`top`是有可能超过`stack_last`；
之后再通过`luaD_call`函数去调用注册的元方法。问题是出现元方法触发时会有可能触发`luaD_reallocstack`对现有的`stack`进行grow，`reallocstack`时并没有对`EXTRA_STACK`中的值做判断。直接做了设置成`nil`。
~~~.c
 for (; lim < newsize; lim++)
    setnilvalue(s2v(newstack + lim)); /* erase new segment */
~~~

因此在`luaT_callTMres`时push参数时，刚好将参数push到了`EXTRA_STACK`中，同时又触发了`reallocstack` 会导致之前设置的参数变成`nil`。这也是为啥上面的测试用例会返回`nil`的原因。因此fix这个问题比较简单，就是在`reallocstack`时跳过`EXTRA_STACK`长度来进行设置`nil`。但是仔细想下当`lua_State`被第一次创建出来时，调用的是`stack_init`函数，此处也并没有将`EXTRA_STACK`中的值做初始化，因此有可能在第一次触发`reallocstack`时会导致之前的`EXTRA_STACK`段会是未初始化的`value`，如果有直接拿着值用的情况下会造成访问一块未初始化的内存，导致crash。所以需要在`stack_init`中也对`EXTRA_STACK`部分设置成`nil`。于是针对这个bug的fix如下:

~~~.diff
diff --git a/ldo.c b/ldo.c
index a60972b2..4b55c31c 100644
--- a/ldo.c
+++ b/ldo.c
@@ -192,7 +192,7 @@ int luaD_reallocstack (lua_State *L, int newsize, int raiseerror) {
     else return 0;  /* do not raise an error */
   }
   for (; lim < newsize; lim++)
-    setnilvalue(s2v(newstack + lim)); /* erase new segment */
+    setnilvalue(s2v(newstack + lim + EXTRA_STACK)); /* erase new segment */
   correctstack(L, L->stack, newstack);
   L->stack = newstack;
   L->stack_last = L->stack + newsize;
diff --git a/lstate.c b/lstate.c
index 42274292..1c7b8791 100644
--- a/lstate.c
+++ b/lstate.c
@@ -181,7 +181,7 @@ static void stack_init (lua_State *L1, lua_State *L) {
   int i; CallInfo *ci;
   /* initialize stack array */
   L1->stack = luaM_newvector(L, BASIC_STACK_SIZE + EXTRA_STACK, StackValue);
-  for (i = 0; i < BASIC_STACK_SIZE; i++)
+  for (i = 0; i < BASIC_STACK_SIZE + EXTRA_STACK; i++)
     setnilvalue(s2v(L1->stack + i));  /* erase new stack */
   L1->top = L1->stack;
   L1->stack_last = L1->stack + BASIC_STACK_SIZE;
~~~
当找到问题之后，我又比较感兴趣的想确认下是什么时候引入这个bug的，因为在测试时发现lua5.3和lua5.4.1均为出现这个bug。于是就看到这个commit [5aa36e894f5a0348dfd19bd9cdcdd27ce8aa5f05](https://github.com/lua/lua/commit/5aa36e894f5a0348dfd19bd9cdcdd27ce8aa5f05)
```
commit 5aa36e894f5a0348dfd19bd9cdcdd27ce8aa5f05
Author: Roberto Ierusalimschy <roberto@inf.puc-rio.br>
Date:   Tue Oct 6 15:50:24 2020 -0300

    No more field 'lua_State.stacksize'
    
    The stack size is derived from 'stack_last', when needed. Moreover,
    the handling of stack sizes is more consistent, always excluding the
    extra space except when allocating/deallocating the array.
```

之前在`lua_State`中是有个字段`stacksize`来记录真实的(包含`EXTRA_STACK`)stack长度。如今是作者可能觉得没必要专门记录这个字段，于是这个字段改成了通过一个macro `#define stacksize(th)    cast_int((th)->stack_last - (th)->stack)`来计算长度了。然而这个macro是不包含`EXTRA_STACK`。所以作者是在修改`stacksize`漏掉了`EXTRA_STACK`才产生了这个bug。 ;D

------

云风已经对skynet 提交这个lua 修复，同时也提交到lua mailist报告这个bug，lua作者roberto也回复确认。