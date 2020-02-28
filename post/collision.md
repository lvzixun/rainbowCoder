## 基于四叉树的碰撞检查

因为新项目的开启，需要把之前的碰撞检测给做些改进和重构；老版本因为代码质量的问题很难在原有的基础上进行做扩充和改进，于是花了一周断断续续的时间把这块给重新了一遍。抛弃了之前划格子做裁枝的实现，改用了四叉树来做。
其实四叉树做裁剪是个比较常规的实现。本身算法也很简单：对整个场景做4个象限划分，依次递归的处理，直到深度达到上限或者最小`node`所能允许的范围上限， 场景中的这些`object`需要根据对应的`AABB`来决定插入到哪个`node`上面去。本质上跟`trie(字典树)`是一样裁枝道理，只是字典树树是可能有多个`child`，四叉树最多是只有4个`child`罢了。代码我就不方便提交到GitHub毕竟是项目的代码，此篇blog主要记录下具体的实现细节，以及我觉得蛮有意思的优化的几个点。

### 内部实现
这个模块最终是会导出给lua去用。所以从最开始，我就不期望自己做任何内存管理，全部都是用`userdata`托管给`lua vm`去管理。虽然相比自己做个内存管理慢一点，但是我觉得现阶段的性能足够可以了，而且就算后来加起来也很快的，所以为了代码的简洁和减少复杂度就暂时没做。

--------

首先通过`new_world(width, height [, deep])`接口创建一个`world`对象，这个对象是个`userdata`，在创建`world`对象时，会给这个`userdata`设置一个`table`类型的`uservalue`。这个`table`中包含两个表，一个是`COLLISION_WORLD_REF`用来记录当前系统创建的除场景对象之外的所有对象引用，另外个表是`OBJID2VALUE_MAP`记录的是`objectID`和`object`对象的映射。所有的对象创建都只会被这两个表中任意一个所持有，为了防止gc被回收掉。只有在调用`remove`接口或者`world`对象被释放时才会被回收。

`width`和`height`这两个参数说明了场景的宽和高，`deep`为可选参数表示需要的树最高的深度是多少。如果不填的会，会根据最小划分的象限为`16`来推算，`width`和`height`会做2的N次幂对齐，最小不会少于`128`； 这里做对齐主要是为了计算象限直接`/2`来判断，使计算象限的开销降为`O(1)`。

------
在创建`world`时只会创建一个`Root node`，不会第一时间将整个完整的四叉树创建出来，而是用时才去创建`node`节点。同时当调用`add_obj(world, objtype, ...)`接口来进行添加对象时并不会立即创建和插入到最深的`node`节点上，而是从`Root node`节点根据对象的`AABB`来找到最合适的一个没有超过`MAX_SPLIT_OBJCOUNT`(16)个的`node`上面，当发现当前`node`上面存储的`object`超过了`MAX_SPLIT_OBJCOUNT`的上限将会触发`split`分裂行为，此时才会将对象插入到所在的4个`child`中。 添加`split`这个策略主要是为了避免如果`world`中对象不多，但是对象移动频繁导致`node`节点个数超过`object`个数，从而造成内存的浪费和查找不必要的开销。 其实到这一步四叉树对于那些比较分散的`object`已经能够做到很好的裁枝以及`O(logN)`的性能了。但是对于那些在一个`node`中跨越多个象限的对象是被存储在`node`上面的，如果当前场景中跨越多个象限的对象很多的话，会导致这些对象被挤压到一个`node`节点中。从而导致查找退化成`O(n)`，于是为了避免这个极端情况，在四叉树原本四个象限的基础上，我又做了个对`node`的优化：
`node`的定义如下:
~~~.c
struct collision_node {
    int deep;
    int node_ref;
    int values_refs[6];
    int values_count;
    int split_count;
    struct collision_aabb bound;
    struct collision_node* children[4];
};
~~~

对于常规的4个象限做如下标记:
```
0   1
2   3
```

完全在`[0-3]`四个象限的对象被放到了`children`中，那些跨越多个象限的对象被放到了`values_refs`中。而且对于这些横跨多个象限的对象根据如下的象限定义做了分类:

```
          -3
       0       1

-2        -1        -4
 
        2      3
          -5

part:-1 values_refs[1]  包含象限: 0, 1, 2, 3
part:-2 values_refs[2]  包含象限: 0, 2
part:-3 values_refs[3]  包含象限: 0, 1
part:-4 values_refs[4]  包含象限: 1, 3
part:-5 values_refs[5]  包含象限: 2, 3
```
那些跨越多个象限的对象会再一次做个分类，放到对应的`values_refs`的槽位中。其中`values_refs[0]`存储的是当前等待分裂到`childern`中的对象，这样能够再一次至少减少25%对象的遍历。
最后我这边简单跟之前的老版本做了性能对比测试：


| module | method |  1M times cost |
|:-----:|:---------------:|:-------:|
| `new_core` | find by circle |  0.251026s |
| `old_gamescene` | find by circle | 0.775125s |
| `new_core` | update obj | 0.424778s | 
| `old_gamescene` | update obj | 1.190214s |


大概有3-4倍的性能提升吧。 

### 碰撞检测
调用`add_obj`接口添加的对象目前只有三类`point(点)`, `circle(圆)`, `polygon(凸多边形)`,是否相交用的是SAT([分离轴算法](https://en.wikipedia.org/wiki/Hyperplane_separation_theorem)) 在此就不再多解释了。 ;D
