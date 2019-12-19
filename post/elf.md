## ELF执行文件本地函数打印

前段时间有同事把我之前写的[luaprofile](https://github.com/lvzixun/luaprofile)工具集成到公司内部基于skynet的通用游戏服务器上面，额外加了火焰图功能，需要帮忙review下代码。
简单来说火焰图就是整个系统每隔一段时间对系统的一个函数调用栈的snapshot集合。他在实现获取函数调用栈是直接遍历[call_frame](https://github.com/lvzixun/luaprofile/blob/master/profile.c#L37-L49)这个struct来实现的，但是因为`call_frame`这个链表只是记录的是从调用`start`开始之后的调用栈，并不是完备的。 

-----
所以最好是遍历lua vm的`callinfo`链表来获取调用栈，所以就顺手写了个在lua5.3.5遍历vm获取调用栈的代码:
~~~.c
#include "lstate.h"
#include "lobject.h"
static int
ldump_callinfo(lua_State* L) {
    CallInfo* ci = L->ci;
    unsigned short n = L->nci;
    int i=0;
    for(i=n-1; i>0 && ci != &(L->base_ci); i--) {
        StkId func = ci->func;
        int t = ttype(func);
        switch (t) {
            // c closure
            case LUA_TCCL: {
                printf("[%d] <CC>c_closure_address:%p\n", i, clCvalue(func)->f);
            }break;

            // light c function
            case LUA_TLCF: {
                printf("[%d] <CF>C_function_address:%p\n", i, fvalue(func));
            }break;

            // lua fucntion
            case LUA_TLCL: {
                Proto *p = clLvalue(func)->p;
                int idx = ci->u.l.savedpc - p->code - 1;
                int curr_line = p->lineinfo[idx];
                printf("[%d] <L>%s:%d\n", i, getstr(p->source), curr_line);
            }break;

            default: {
                luaL_error(L, "invalid callinfo func type:%d", t);
            }break;
        }
        ci = ci->previous;
    }
    return 0;
}
~~~
写完发现，在整个调用栈中有些是C函数，这些c函数只能打印出来一个函数地址，而不是列数来函数名字。于是就想能否转换成对应的函数名？简单Google下就发现有个`dladdr`函数是可以支持给定一个函数指针返回函数名称。
所以我就在我自己的macosx机器上面简单的测试了下`dladdr`这个函数，发现不论是导出函数还是`static`函数，都可以查到名字。于是就很满意的跟同事说了可以用`dladdr`来获取函数名。

但他尝试了下发现在Linux机器上面是无法获取`static`函数的名字，导出函数的名字是没问题的。看来是`dladdr`这个函数在macosx和Linux下面的实现是有差别的。于是查了半天的文档，发现编译生成的elf执行文件中并不是没有`static`函数的名字，而是与导出函数区别对待: `static`函数放在了`.symtab`；导出函数是放在`.dynsym`中。Linux的`dladdr`实现是只查了`.dynsym`这一个表，所以会导致找不到`static`函数。

----
如果要想导出`static`函数的名字，只能去查询ELF文件格式，根据[ELF FORMAT](https://en.wikipedia.org/wiki/Executable_and_Linkable_Format)自己分析
`so`或者`.out`这些elf文件，找到`.symtab`中所在的位置，读取对应的函数偏移量来定位名称。最后我实现了[elfaddr](https://gist.github.com/lvzixun/70fc46816e6b67b50d330e11578b58d8) 这个函数能够查询`static `函数。;D

输出效果如下:
~~~.c
[11] <CF>C_function_address:0x1067c9160file:/codes/skynet/luaclib/skynet.so name:ldump_callinfo
[10] <L>@./test/ts2.lua:15
[9] <L>@./test/ts2.lua:17
[8] <L>@./test/ts2.lua:19
[7] <L>@./test/ts2.lua:32
[6] <L>@./lualib/skynet.lua:746
[5] <CF>C_function_address:0x105de0250file:/codes/skynet/./skynet name:luaB_xpcall
[4] <L>@./lualib/skynet.lua:750
[3] <L>@./lualib/skynet.lua:754
[2] <L>@./lualib/skynet.lua:767
[1] <L>@./lualib/skynet.lua:114
~~~
