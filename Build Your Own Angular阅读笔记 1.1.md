#Build Your Own Angular阅读笔记(scope and digest)
##脏值检测的本质

```javascript
function Scope() {this.$$watchers = []; }

Scope.prototype.$watch = function(watchFn, listenerFn) { var watcher = {
    watchFn: watchFn,
    listenerFn: listenerFn
};
this.$$watchers.push(watcher); 
};}

Scope.prototype.$digest = function() { _.forEach(this.$$watchers, function(watcher) {
    watcher.listenerFn();
  });
};
```
作用域拥有一组观察者变量，$watch方法负责向观察者数组添加新成员。整个脏值检测过程通过$digest循环驱动，根据watchFn的结果，来决定listenerFn是否需要被调用。

##如何给监测变量赋初值
该变量的初值必须是唯一的，即与该变量严格相等的变量/值只能是它自己。
```javascript
function initWatchVal() { }
Scope.prototype.$watch = function(watchFn, listenerFn) { var watcher = {
    watchFn: watchFn,
    listenerFn: listenerFn,
    last: initWatchVal
};
this.$$watchers.push(watcher); };
```
答案是函数的引用地址。
该函数被定义在闭包内，所以在系统运行时，外部不存在任何变量的值与它相等。

##如何驱动脏值检测循环
如果新值与旧值不相等，则说明该变量是”脏“的，需继续检测。
```javascript
Scope.prototype.$$digestOnce = function() {
var self = this;
var newValue, oldValue, dirty; _.forEach(this.$$watchers, function(watcher) {
newValue = watcher.watchFn(self); oldValue = watcher.last;
if (newValue !== oldValue) {
      watcher.last = newValue;
      watcher.listenerFn(newValue,
		(oldValue === initWatchVal ? newValue : oldValue),
		self
		); 
dirty = true;
} });
return dirty; };

//外层循环
Scope.prototype.$digest = function() { var dirty;
do {
dirty = this.$$digestOnce(); } while (dirty);
};
```
**改进1**
外层循环的写法可以进一步改进，增加最大循环次数(比如10次)，超过最大次数后强行退出脏值检测循环，以避免无限循环检测的情况（两个watcher中互相修改对方的值）。

**改进2**
为了减少每次$$digestOnce()的工作量，增加一个变量$$lastDirtyWatch记录上一次脏值检测的watcher,如果两次相同，则直接从对$$watchers的遍历中跳出。
注: 回调函数中 return false的功能是终止_.foreach()遍历，而非continue。

*comments*
>先吐槽，这种优化方式非常蠢，优化点并不明显，并没有从本质上降低算法的时间复杂度，在最坏情况下（下文举例），没有降低计算次数。当然，从能优化一点是一点的角度，这也算是'优化'。
>使用$$lastDirtyWatch记录上一次脏值检测的watcher，只有当$$lastDirtyWatch在$$digestOnce()遍历顺序靠前时才会有优化效果，若上次脏值检测刚好位于遍历顺序的最后一位，则没有优化效果。
```javascript
        it("ends the digest when the last watch is clean", function() {
            scope.array = _.range(100);
            var watchExecutions = 0;
            _.times(100, function(i) {
                scope.$watch(
                    function(scope) {
                        watchExecutions++;
                        return scope.array[i];
                    },
                    function(newValue, oldValue, scope) {});
            });
            scope.$digest();
            expect(watchExecutions).toBe(200);
            // scope.array[0] = 420;
            scope.array[99] = 420;//直接改动遍历顺序中的最后一个watcher
            scope.$digest();
            // expect(watchExecutions).toBe(301);
            expect(watchExecutions).toBe(400);//仍然会算400次
        });
```
*comments plus*
>看来AngularJs使用粗暴的循环脏值检测被广泛吐槽的现象并不是没有道理，如果采用'生产者-消费者'模型来重新设计$digest过程，可以最大限度的利用v8引擎的异步多线程能力，效率自然更高。不需要采用上文提及的恶心的优化方式。

**改进3**
向外部开放valueEq参数，用以标记是否是由值相等(_.equal() )的方式判断newValue,oldValue相等，及是否使用深拷贝方式对watcher.last进行赋值。
```javascript
Scope.prototype.$$digestOnce = function() {
    var self = this;
    var newValue, oldValue, dirty;
    _.forEach(this.$$watchers, function(watcher) {
        newValue = watcher.watchFn(self);
        oldValue = watcher.last;
        if (!self.$$areEqual(newValue, oldValue, watcher.valueEq)) {//!
            self.$$lastDirtyWatch = watcher;
            watcher.last = (watcher.valueEq ? _.cloneDeep(newValue) : newValue);//!
            watcher.listenerFn(newValue,
                (oldValue === initWatchVal ? newValue : oldValue),
                self);
            dirty = true;
        } else if (self.$$lastDirtyWatch === watcher) {
            return false;
        }
    });
    return dirty;
};
```
**改进4**
js中值NaN永远与自身不相等，需要特殊处理。

>体现框架的严谨性

##$eval、$apply、$evalAsync
目前的$eval就是一个简单的执行传入函数的函数
```javascript
Scope.prototype.$eval = function(expr, locals) {
	return expr(this, locals); 
};
```
$apply接收一个函数参数，执行$eval后触发digest循环，仅此而已。
```javascript
Scope.prototype.$apply = function(expr) {
    try {
        return this.$eval(expr);
    } finally {
        this.$digest();
    }
};
```
这东西的存在意义，就是将外部代码的运行纳入到AngularJs的生命周期中去。

$evalAsync是异步的$eval，需注意其与单纯的setTimeout之间的区别，$evalAsync会强制在每次digestOnce后执行，而setTimeout则把什么时候执行的权限交给浏览器。通过在scope内维护一个$$asyncQueue异步消息队列，同时在每次$digest循环中，取出队列中的任务进行处理。

```javascript
function Scope() {
    this.$$watchers = [];
    this.$$lastDirtyWatch = null;
    this.$$asyncQueue = [];
}

Scope.prototype.$evalAsync = function(expr) {
    this.$$asyncQueue.push({ scope: this, expression: expr });
};

Scope.prototype.$digest = function() {
    var ttl = 10;
    var dirty;
    this.$$lastDirtyWatch = null;
    do {
        while (this.$$asyncQueue.length) {
            var asyncTask = this.$$asyncQueue.shift();
            asyncTask.scope.$eval(asyncTask.expression);
        }
        dirty = this.$$digestOnce();
        if ((dirty || this.$$asyncQueue.length) && !(ttl--)) {
            throw "10 digest iterations reached";
        }
        //应改为
        //if (!(ttl--)) {
        //    throw "10 digest iterations reached";
        //}
        //外层循环已有判断，内层应只关注ttl
    } while (dirty || this.$$asyncQueue.length);
};
```

*comments*
>原书中为了处理watchFn内出现$evalAsync(如下文代码所示)增加了this.$$asyncQueue.length<=0的循环终止条件,然而do代码块里也出现了同样的判断条件，相当得蠢。

```javascript
scope.$watch(function(scope) {
   scope.$evalAsync(function(scope) {});
   return scope.aValue;
   },
   function(newValue, oldValue, scope) {});
```

**让$evalAsync有驱动digest循环的能力**
给scope增加$$phase对象，及相关方法，该对象目前有三种值，"$digest"、"$apply"和null,分别表示当前scope所处的状态，只有当$$phase为null且异步队列中有值时，$evalAsync才会驱动digest循环。$$phase对象的状态由$digest、$apply方法改变。
```javascript
Scope.prototype.$evalAsync = function(expr) {
    var self = this;
    if (!self.$$phase && !self.$$asyncQueue.length) {
        setTimeout(function() {
            if (self.$$asyncQueue.length) {
                self.$digest();
            }
        }, 0);
    }
    this.$$asyncQueue.push({ scope: this, expression: expr });
};
```

##$applyAsync##
$applyAsync并不能单单的看做$apply的异步版(可能$evalAsync更像一点)，$applyAsync的功能除了在异步下驱动digest循环外，一个很重要的功能是"在一次digest循环中合并近期所有的异步操作"。这样可以大幅降低同时发起多次异步操作的场景下，页面渲染的效率。“没有必要渲染那些马上就会被复写的界面元素”，考虑到scope中的对象与dom元素有直接的关联，这一优化效果是指数级的。

首先，在scope中加入$$applyAsyncQueue(有别于$evalAsync所使用的$$asyncQueue)
```javascript
function Scope() {
    this.$$watchers = [];
    this.$$lastDirtyWatch = null;
    this.$$asyncQueue = [];
    this.$$applyAsyncQueue = [];
    this.$$phase = null;
}
```

$applyAsync向操作队列里push操作对象，用setTimeout异步执行"从队列中取值->执行操作"
```javascript
Scope.prototype.$applyAsync = function(expr) {
    var self = this;
    self.$$applyAsyncQueue.push(function() {
        self.$eval(expr);
    });
    setTimeout(function() {
        self.$apply(function() {
            while (self.$$applyAsyncQueue.length) {
                self.$$applyAsyncQueue.shift()();
            }
        });
    }, 0);
};
```

**$$applyAsyncId标识**
为了防止多次调用$applyAsync导致$apply重复执行的情况，在scope中增加属性，$$applyAsyncId，
```javascript
function Scope() {
	//...
    this.$$applyAsyncId = null;
}
```
$$applyAsyncId只有两种值，1、null，2、setTimeout的返回值(setTimeout返回一个全局唯一的id,可被用作cancel该异步操作)
```javascript
Scope.prototype.$applyAsync = function(expr) {
    var self = this;
    self.$$applyAsyncQueue.push(function() {
        self.$eval(expr);
    });
    if (self.$$applyAsyncId === null) {
        self.$$applyAsyncId = setTimeout(function() {
            self.$apply(function() {
                while (self.$$applyAsyncQueue.length) {
                    self.$$applyAsyncQueue.shift()();
                }
                self.$$applyAsyncId = null;
            });
        }, 0);
    }
};
```

**与$digest的联动**
```javascript
                scope.$applyAsync(function(scope) {
                    scope.aValue = abc;
                });
                scope.$applyAsync(function(scope) {
                    scope.aValue = def;
                });
                scope.$digest();
                expect(scope.counter).toBe(2);
                expect(scope.aValue).toEqual(def);
                setTimeout(function() {
                    expect(scope.counter).toBe(2);
                    done();
                }, 50);
```
当用户主动调用$digest时，就没有必要再让已有的$applyAsync多触发一次了，取出$$applyAsyncQueue中的操作，并直接执行。

```javascript
	//...
   if (this.$$applyAsyncId) {
        clearTimeout(this.$$applyAsyncId);
        this.$$flushApplyAsync();
    }
    do {
        while (this.$$asyncQueue.length) {
            var asyncTask = this.$$asyncQueue.shift();
            asyncTask.scope.$eval(asyncTask.expression);
			//...

```

##$postDigest
$$postDigest的功能与$evalAsync近似，都是将一部分代码延后执行，区别在于，$evalAsync会主动触发digest循环，而$$postDigest是严格地将这部分代码放在下一次digest循环后执行，并且不会主动触发digest。
实现的套路也与它的兄弟们近似，在scope中新增队列$$postDigestQueue，然后在每次digest循环结束时处理它。
```javascript
function Scope() {
    this.$$watchers = [];
    this.$$lastDirtyWatch = null;
    this.$$asyncQueue = [];
    this.$$applyAsyncQueue = [];
    this.$$applyAsyncId = null;
    this.$$postDigestQueue = [];
    this.$$phase = null;
}

Scope.prototype.$digest = function() {
	...
    do {
        ...
    } while (dirty || this.$$asyncQueue.length);
    this.$clearPhase();
    while (this.$$postDigestQueue.length) {
        this.$$postDigestQueue.shift()();
    }
};
```

##异常处理
简单来说就是$$digestOnce、$digest等涉及对watcher、listener、各种操作队列内存放的函数直接调用的地方，加上try..catch。具体代码参见原书。

##watcher的销毁
简单地实现这个功能就是：$watch返回一个函数，该函数负责清理这个watcher。
```javascript
Scope.prototype.$watch = function(watchFn, listenerFn, valueEq) {
    var self = this;
    var watcher = {
        watchFn: watchFn,
        listenerFn: listenerFn,
        valueEq: !!valueEq,
        last: initWatchVal
    };
    self.$$watchers.push(watcher);
    this.$$lastDirtyWatch = null;
    return function() {
        var index = self.$$watchers.indexOf(watcher);
        if (index >= 0) {
            self.$$watchers.splice(index, 1);
        }
    };
};
```

**在digest里销毁$watcher**
考虑下面这种情况，第二个watcher中，调用了自身的销毁函数，destroyWatch将会在digest循环内被触发。这会导致第三个watcher在digest循环中被跳过。
```javascript
scope.$watch( function(scope) {
     watchCalls.push('first');
     return scope.aValue; 
   }
);
var destroyWatch = scope.$watch( function(scope) {
      watchCalls.push('second');
      destroyWatch();
    }
);

scope.$watch(function(scope) {
    watchCalls.push('third');
    return scope.aValue;
});
```
>第三个watcher被跳过的原因：
>目前digestOnce内遍历的实现是这样的，
>_.forEach(this.$$watchers, function(watcher) {
>   newValue = watcher.watchFn(self);
>   ...
>}
>在watchFn被调用时，即调用了destroyWatch，删除了this.$$watchers中的index为1元素，数组中index为2的元素(最后一个)被补到了index 1上，循环终止。原本index为2的元素被跳过。

解决方法是反向遍历，并且将新的watcher加在数组的头部。
```javascript
Scope.prototype.$watch = function(watchFn, listenerFn, valueEq) {
  ...
  //self.$$watchers.push(watcher);
  this.$$watchers.unshift(watcher);
}

Scope.prototype.$$digestOnce = function() {
    //_.forEach(this.$$watchers, function(watcher) {
    _.forEachRight(this.$$watchers, function(watcher) {
		...
    })
}
```

**在一个watcher里销毁另一个watcher**
同样是销毁watcher时元素偏移的问题
```javascript
scope.$watch(
    function(scope) {
        return scope.aValue;
    },
    function(newValue, oldValue, scope) {
        destroyWatch();
    }
);
var destroyWatch = scope.$watch(function(scope) {}, function(newValue, oldValue, scope) {});
scope.$watch(
    function(scope) { return scope.aValue; },
    function(newValue, oldValue, scope) {
        scope.counter++;
    }
);
```
第一个watcher在第一次digestOnce遍历中会删除第二个watcher，它自己又会被补位到第二个watcher原来的位置上去。于是，*第一个watcher被执行了两遍！*。这样带来的问题是$$lastDirtyWatch，这个原本用于优化遍历次数的变量出现问题，因为$$lastDirtyWatch会记录上一个"脏变量"，而第一个watcher在一次循环中被连续执行了两遍，会使得循环直接退出遍历，第三个watcher就永远没法执行了。
解决方法很简单，在watcher的销毁函数中将$$lastDirtyWatch置空.
```javascript
Scope.prototype.$watch = function(watchFn, listenerFn, valueEq) {
	...
    return function() {
        var index = self.$$watchers.indexOf(watcher);
        if (index >= 0) {
            self.$$watchers.splice(index, 1);
            self.$$lastDirtyWatch = null;
        }
    };
};
```

**在一个watcher里销毁多个watcher**
当出现一个watcher里删除多个watcher的情况，会导致_.forEachRight(_.forEach也一样)遍历到被删除的变量,此时变量值为undefined,所以需要在访问iteratee前检查。
>lodash的forEach是根据**遍历开始时**数组的大小决定遍历次数的，遍历过程中存在iteratee指向空值的可能。与此相对的，javascript原生的Array.foreach在遍历过程中会自动跳过空值元素。

##$watchGroup
$watchGroup是AngularJs1.3之后才加入的功能，一组watcher对应一个listener。

首先，可以单纯的把一个watchGroup拆成若干个watch。如下所示：
```javascript
Scope.prototype.$watchGroup = function(watchFns, listenerFn) {
    var self = this;
    _.forEach(watchFns, function(watchFn) {
        self.$watch(watchFn, listenerFn);
    });
};
```
如此简单粗暴的实现是不合适的。如果监听的多个对象同时都发生了变化，listener将会被调用多次。我们的目的是只响应一次，而且在上述情况下listener里的oldValue和newValue的值是无法确定的。

基本思路仍然是把一个watchGroup拆成若干个watch，只是在拆分的时候，对每个watch的listener做点手脚。首先，使用$evalAsync将listener的执行放在本次$digest循环后，然后避免重复执行listener，用changeReactionScheduled这个开关变量控制，这样对于一个watchGroup而言，它的listener在一次digestOnce中至多执行一次，且在digestOnce主体执行完毕后执行(保证所有watcher都被响应)。

```javascript
Scope.prototype.$watchGroup = function(watchFns, listenerFn) {
    var self = this;
    var oldValues = new Array(watchFns.length);
    var newValues = new Array(watchFns.length);
    var changeReactionScheduled = false;

    function watchGroupListener() {
        listenerFn(newValues, oldValues, self);
        changeReactionScheduled = false;
    }
    _.forEach(watchFns, function(watchFn, i) {
        self.$watch(watchFn, function(newValue, oldValue) {
            newValues[i] = newValue;
            oldValues[i] = oldValue;
            if (!changeReactionScheduled) {
                changeReactionScheduled = true;
                self.$evalAsync(watchGroupListener);
            }
        });
    });
};
```









