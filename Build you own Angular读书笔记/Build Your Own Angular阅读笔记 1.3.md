# Build Your Own Angular阅读笔记(Watching Collections)
本章主要介绍了对$watch的扩展方法——$watchCollection。$watch方法的第三个参数可以控制观察变量是否被"深度监测"。$watchCollection实现的是"浅监测"(只监测深度为1的变化)，一般情况下，浅监测就可以满足需求，且提升了运行效率。
## 基础结构
实现$watchCollection的基本思路是，将传入的watchFn、listenerFn函数外包一层函数，再传入$watch方法。
internalWatchFn负责包裹watchFn，返回值是一个记录监测值改变次数的计数变量changeCount。这样对于$watch方法而言，当监测值发生改变时，changeCount也会发生变化，$watch方法实际上响应的是changeCount值的改变。
internalListenerFn负责包裹listenerFn，listenerFn肩负着将newValue，oldValue传递出去的重任，自然不能用changeCount糊弄过去，$watchCollection自身拥有newValue、oldValue，internalWatchFn负责更新这两个变量，internalListenerFn负责将这两个变量传递给listenerFn。
```javascript
Scope.prototype.$watchCollection = function (watchFn, listenerFn) {
    var self = this;
    var newValue;
    var oldValue;
    var changeCount = 0;
    var internalWatchFn = function (scope) {
        newValue = watchFn(scope);
        if (!self.$$areEqual(newValue, oldValue, false)) {
            changeCount++;
        }
        oldValue = newValue;
        return changeCount;
    };
    var internalListenerFn = function () {
        listenerFn(newValue, oldValue, self);
    };
    return this.$watch(internalWatchFn, internalListenerFn);
};
```
>下文中对监听值为对象（数组、对象）时的处理方法可以被大致归纳为：构造一个独立空间的oldValue,通过比较newValue、oldValue间深度为1的值，自定义一系列操作将oldValue”还原“至newValue。

>js里”深拷贝“本来也是个坑，一个深拷贝函数需要考虑的内容包括但不限于：存在引用环的对象、复制对象的原型链、函数对象


## 数组检测
对数组的检测由以下若干个环节组成：
* 判断被监测值是否为一个数组，且oldValue不是数组。如果满足条件，则创建一个新数组。
* 检测数组中是否新增/删除了某些元素(数组长度是否发生改变)
* 检测数组中的每项是否发生改变
* 针对Array-Like对象的特殊处理

```javascript
var internalWatchFn = function (scope) {
    newValue = watchFn(scope);
    if (_.isObject(newValue)) {
        if (_.isArrayLike(newValue)) {
            if (!_.isArray(oldValue)) {
                changeCount++;
                oldValue = [];
            }
            if (newValue.length !== oldValue.length) {
                changeCount++;
                oldValue.length = newValue.length;
                //为什么不能直接用oldValue=newValue？
            }
            _.forEach(newValue, function (newItem, i) {
                var bothNaN = _.isNaN(newItem) && _.isNaN(oldValue[i]);
                if (!bothNaN && newItem !== oldValue[i]) {
                    changeCount++;
                    oldValue[i] = newItem;
                }
            });
        } else {
        }
    } else {
        if (!self.$$areEqual(newValue, oldValue, false)) {
            changeCount++;
        }
        oldValue = newValue;
    }
    return changeCount;
};
```
>Array-Like是指这样一种对象：有length属性，也可以通过索引的方式访问arr_like[0]，但是并不具备Array.prototype里的方法。Array-Like包括但不限于arguments、dom的nodeList。

>关于“为什么不能直接用oldValue=newValue”的问题这里再次说明，因为newValue = watchFn(scope);这一步说明newValue存放的永远是被监测值的“引用”，从外部修改被监测值会导致newValue的引用值直接发生变化，如果再使用oldValue=newValue就会直接形成一个连等式 oldValue==newValue==watchFn(scope) 这样也就无从判断newValue与oldValue之间的差异了。下文对于对象的处理同理。

## 对象检测
对对象的检测与数组类似，分为以下几个步骤：
* 判断被监测值是否是一个对象，且oldValue不是对象或是一个Array-Like对象,如果满足条件，则创建一个新对象
* 检测对象中是否有新增或被改变的属性
* 检测对象中是否有被删除的属性

```javascript
var internalWatchFn = function (scope) {
    var newLength;

    newValue = watchFn(scope);
    if (_.isObject(newValue)) {
        ...
        //数组的判断部分省略
        } else {
            if (!_.isObject(oldValue) || isArrayLike(oldValue)) {
                changeCount++;
                oldValue = {};
                oldLength = 0;
            }
            newLength = 0;
            _.forOwn(newValue, function (newVal, key) {
                newLength++;
                if (oldValue.hasOwnProperty(key)) {
                    var bothNaN = _.isNaN(newVal) && _.isNaN(oldValue[key]);
                    if (!bothNaN && oldValue[key] !== newVal) {
                        changeCount++;
                        oldValue[key] = newVal;
                    }
                } else {
                    changeCount++;
                    oldLength++;
                    oldValue[key] = newVal;
                }
            });
            if (oldLength > newLength) {
                changeCount++;
                _.forOwn(oldValue, function (oldVal, key) {
                    if (!newValue.hasOwnProperty(key)) {
                        oldLength--;
                        delete oldValue[key];
                    }
                });
            }
        }
    } else {
        if (!self.$$areEqual(newValue, oldValue, false)) {
            changeCount++;
        }
        oldValue = newValue;
    }

    return changeCount;
};
```
代码里还包含了一部分细节上的处理，包括针对NaN的处理，引入newLength、oldLength变量对比较时的迭代次数进行优化，对含'length'属性的对象的甄别等等，不再赘述。

## veryOldValue
这部分处理将真正的oldValue传递给Listener的问题，（internalWatchFn的oldValue只是用作与newValue比较，函数执行完以后，两者的值是相同的。）

```javascript
Scope.prototype.$watchCollection = function (watchFn, listenerFn) {
            ...
            var veryOldValue;
            var trackVeryOldValue = (listenerFn.length > 1);
            var firstRun = true;

            var internalListenerFn = function () {
                if (firstRun) {
                    listenerFn(newValue, newValue, self);
                    firstRun = false;
                } else {
                    listenerFn(newValue, veryOldValue, self);
                }

                if (trackVeryOldValue) {
                    veryOldValue = _.clone(newValue);
                }
            };

            return this.$watch(internalWatchFn, internalListenerFn);
        };
```

关于listenerFn.length的解释，一个函数的length表示函数形参的个数，trackVeryOldValue其实是为了判断使用者在定义回调函数listenerFn时是否定义了oldValue这一参数，比如Scope.$watch('varA',function(newValue){})这种情况下，就可以省去每次深拷贝newValue的开销（因为用户不需要知道oldValue的值） 

>精打细算到如此程度！















