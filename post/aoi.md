## AOI

对于AOI(area if interest)介绍的文章实在是太多了，比如常用的灯塔，9grid，十字链表等等，这些本质上是在面对海量的数据量做裁枝。最近同事聊起来说在做AOI优化部分的工作，于是就感兴趣跟他聊起来现在的实现，以及优化的方向。 其实现在的实现就是最最标准和简单的9 grid的实现。 每次对象在`add`, `move`, `delete`时，会返回一个集合，表示需要通知的其他对象。 当如果N个对象全部都是在同一个grid里面而且同时产生事件，那这个简单的算法会是O(NxN)的性能开销。 

-----

我觉得，对于aoi来说，所做的事情就只有一件事情，根据此时的snapshot，和上一次的snapshot对比生成diff（变化的对象），返回给对应的watcher(观察者)。在这段时间内假如A对象从 b点移动到了c点，但又回到了c点，diff里面将不会包含这个A对象移动的信息。 驱动`AOI`工作应该是每次调用`update`，并不是在操作函数`add`, `move`, `delete`。 这样，可以自己决定在合适的时机(比如在每帧末尾或者固定时间执行)调用`update`获得这段时间需要通知的事件集合，这样在面对之前N个对象在同一个grid同时移动的时间开销将会降到O(N)。 
但是对每个watcher创建snapshot开销太大，在同一个grid里面的watcher中的snapshot是一样的，所以可以只需要对grid做snapshot，不过这样被修改的grid对象会存储翻倍，而且每次`update`时要生成snapshot，性能上肯定会无法接受。 

其实对于snapshot本身只是为了diff，那其实可以在grid上记录下两次`update`之间的改动，在`update`时直接根据改动来生成diff列表，之后再把改动合并到grid存储objects的集合中就好，这样就避免对整个grid的snapshot。 
所以我就实现了 [AOI](https://github.com/lvzixun/aoi)来证明了想法。 ;D

### AOI 内部实现
首先你可以通过`aoi.aoi_new(map_row, map_col, grid_row, grid_col)`来构建一个`aoi_obj`，`aoi_obj:aoi_add(obj_id, marked, pos_x, pos_y)`接口来向aoi 场景中添加一个对象id为`obj_id`的object，所有的object可以是watcher，maker，或者同时为两者。 只有watcher才会收到maker产生的事件，watcher之间不会产生任何事件。 `aoi_obj:aoi_remove(obj_id)
`函数为移除一个对象, `aoi_obj:aoi_set(obj_id, pos_x, pos_y)`更新一个对象，以及`aoi_obj:aoi_update()`更新整个aoi对象，返回需要通知的watchers的makers事件。 事件分为三类`D`删除，`A`添加，`U`更新。 每个对象的更新会根据`grid_row`和`grid_col`被存储在对应的grid对象上。 `grid_obj`的定义如下：

~~~.lua
    local obj = {
        aoi_obj = aoi_obj,
        grid_idx = grid_idx,
        watchers = false,
        objs = {},
        touchs = false,
        merge = false,
        result = {},
    }
~~~
其中`watchers`记录了当前grid上面的所有watcher对象id，`objs`记录的是上一次`update`之后当前grid的object，`touchs`记录的从上一次`update`到现在grid上面有改动的对象信息，其中merge和result是在update时会用到的字段。 `aoi_add`, `aoi_set`, `aoi_remove`这些接口最后都会设置到对应的grid的`touchs`中。当执行`update`时，会计算出需要通知的有watcher的grids， 对每个grid的周围的9个grid下生成对应的diff，每个grid的diff会最多包含以下三种:`GD` grid中object被删除事件集，`GA`grid中object被添加事件集，`GU`grid中object更新事件集。这些结果会存储到`result` table中。 之后根据每个watcher来选择对应的结果集，避免反复的计算。

在`update`实现时这里有个优化：是从被touch的grid来找到那些watcher，还是从有watcher的grid来找到那些grid被touch。 当被touch的grid大于有watch 的grid个数，会选择直接从有watcher的grid去处理。反之，从touch的grid来处理。这样的好处是避免了，update在watcher和 touch的maker差距很大时，无效的遍历。 

------ 

最终我在自己机器`Intel(R) Core(TM) i7-4578U CPU @ 3.00GHz`上面测试了在同一个grid添加10K个对象，仅仅只需要0.028496s. 
