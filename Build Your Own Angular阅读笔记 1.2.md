# Build Your Own Angular阅读笔记(Scope Inheritance)
## 作用域的继承
AngularJs中的作用域继承机制就是javascript的原型链继承，因为它就是这么实现的。这里需要注意，这种实现方式意味着ChildScope在构造时并没有Scope构造函数里所拥有的对象。
```javascript
Scope.prototype.$new = function() {
    var ChildScope = function() {};//构造函数是空的
    ChildScope.prototype = this;
    var child = new ChildScope();
    return child;
};
```
>这正好是个深入理解原型链继承的好机会，事实上我又把《你不知道的JavaScript-上卷》第五章看了一遍。
>下面的代码与上文代码对比有什么区别？
```javascript
var ChildScope = new Scope();
```
>区别在于new Scope()会调用Scope()这个构造函数，而var child = new ChildScope()调用的是ChildScope(),ChildScope是个空函数，所以严格的说var child = new ChildScope(); child里并没有$$watchers[]、$$asyncQueue[] 这些属性。再看ChildScope.prototype = this，其实当你访问ChildScope.$$watchers[]时，你访问的其实是$rootScope里的$$watchers（原型链一级一级的找上去）。
>那当我把写法换成ChildScope.prototype = Scope.prototype能有同样的效果吗？答案是不行。因为 Scope.prototype里没有$$watchers[]，此时的原型链是ChildScope->Scope.prototype，而前面的写法原型链是ChildScope->Scope->Scope.prototype，少了一级，所以是访问不了ChildScope.$$watchers[]的。

## Attribute Shadowing
名词解释，Attribute Shadowing是指在如下的测试用例中，parent.name的值在child中被child.name所遮蔽。
```javascript
it("shadows a parent s property with the same name", function() {
    var parent = new Scope();
    var child = parent.$new();
    parent.name = 'Joe';
    child.name = 'Jill';
    expect(child.name).toBe('Jill');
    expect(parent.name).toBe('Joe');
});
```
但是，在一些情况下不会，
```javascript
it("does not shadow members of parent scope s attributes", function() {
    var parent = new Scope();
    var child = parent.$new();
    parent.user = { name: 'Joe' };
    child.user.name = 'Jill';
    expect(child.user.name).toBe('Jill');
    expect(parent.user.name).toBe('Jill');
});
```
原因就是parent.user和child.user的值都是同一个js对象的引用，child.user.name = 'Jill'只是改变了引用对象内的值，与parent和child无关。
>其实在AngularJs里层层嵌套的scope中，这种特性倒能称得上是“良性bug”，当使用者想将child内值的变化传递给parent时，这是最方便的办法。以往开发时遇到的"ngModel必须加上一个'点'的问题"就是由该原因导致的。
>但是，这种特性实在是令人confusing,且会使得作用域之间的关系变得错综复杂，或许这也是AngularJs设计失败的地方之一。

## 给每个scope准备单独的watchers
按照现有scope的定义，当你watch一个child scope中的变量时，这个watcher实际上是被push到了root scope中，即child scope的 digest循环执行的其实是root scope的watcher队列。就像这样，
```javascript
it("does not digest its parent(s)", function() {
    var parent = new Scope();
    var child = parent.$new();
    parent.aValue = abc;
    parent.$watch(
        function(scope) { return scope.aValue; },
        function(newValue, oldValue, scope) {
            scope.aValueWas = newValue;
        }
    );
    child.$digest();
    expect(child.aValueWas).toBeUndefined();
});
```
解决方法就是在new一个scope的时候，将一个新的watchers添加到child scope中。
```javascript
Scope.prototype.$new = function() {
    var ChildScope = function() {};
    ChildScope.prototype = this;
    var child = new ChildScope();
    child.$$watchers = [];
    return child;
};
```

## digest的递归调用
对于parent scope的digest调用，应当能够触发其所有descendant scope的digest。
首先在scope中添加其子节点的存储数组，并在$new方法里对其初始化。

```javascript
function Scope() {
	...
    this.$$children = [];
}

Scope.prototype.$new = function() {
	...
    this.$$children.push(child);
    child.$$children = [];
    return child;
};
```

接着定义一个辅助函数，递归地访问所有子节点，并调用指定的函数。
```javascript
Scope.prototype.$$everyScope = function(fn) {
    if (fn(this)) {
        return this.$$children.every(function(child) {
            return child.$$everyScope(fn);
        });
    } else {
        return false;
    }
};
```

最后利用$$everyScope改造$$digestOnce方法，使得$$digestOnce能递归地处理所有子scope，外层增加了控制变量continueLoop，用来标记是否退出迭代。
```javascript
Scope.prototype.$$digestOnce = function() {
    var dirty;
    var continueLoop = true;
    var self = this;
    this.$$everyScope(function(scope) {//everyScope
        var newValue, oldValue;
        _.forEachRight(scope.$$watchers, function(watcher) {
            try {
                if (watcher) {
                    newValue = watcher.watchFn(scope);
                    oldValue = watcher.last;
                    if (!scope.$$areEqual(newValue, oldValue, watcher.valueEq)) {
                        self.$$lastDirtyWatch = watcher;
                        watcher.last = (watcher.valueEq ? _.cloneDeep(newValue) : newValue);
                        watcher.listenerFn(newValue,
                            (oldValue === initWatchVal ? newValue : oldValue),
                            scope);
                        dirty = true;
                    } else if (self.$$lastDirtyWatch === watcher) {
                        continueLoop = false;//continueLoop控制变量
                        return false;
                    }
                }
            } catch (e) {
                console.error(e);
            }
        });
        return continueLoop;
    });
    return dirty;
};
```

## 让$apply, $evalAsync, $applyAsync能够触发整个scope树的digest
划重点，在AngularJs里，$apply和$digest最大的区别就是，$apply触发的是整个树的digest，而$digest触发的是对应的scope(及其子节点)的digest。如果追求效率，就不要轻易的使用$apply，而多用digest替代。
首先在scope里加上一个变量$root，指向根节点，
```javascript
function Scope() {
	...
	this.$root = this;
}
```
然后在$apply里触发的digest实际上是$rootscope的。
```javascript
Scope.prototype.$apply = function(expr) {
    try {
        this.$beginPhase($apply);
        return this.$eval(expr);
    } finally {
        this.$clearPhase();
        this.$root.$digest();
    }
};
```
按照上文的介绍，祖先作用域的digest实际上递归调用了其所有子孙节点的digest，又因为AngularJs里$root只有一个，所以$root的digest实际上触发了整个树的digest。
对$evalAsync,$applyAsync这些方法的改造同理。

现在又要开始折腾$$lastDirtyWatch这个变量了，原书中的描述是"We should always refer to the $$lastDirtyWatch of root, no matter which scope $digest was called on"，并没有说明为什么。
这里给出说明。
首先需要明确的是，$$lastDirtyWatch这个变量只对一次$digest有效(指一次整体的$digest，而不是$digestOnce),所以$$lastDirtyWatch其实可以(或者说应该)被做成全局唯一的变量。然后，目前所有scope都有自己的$$lastDirtyWatch（在this.$$lastDirtyWatch = null时创建），但是置空这个变量的时间点，又是在对这个scope进行$digest操作的时候。换句话说，对这个scope的子scope进行递归$digestOnce操作时并不会置空子scope的$$lastDirtyWatch，但是用户难免会在父scope中修改子scope里的值，这就会导致$$lastDirtyWatch错误的取消掉原本应该执行的脏值检测过程。
所以，综上所述，解决办法只有所有的scope都使用$root.$$lastDirtyWatch。
```javascript
Scope.prototype.$digest = function() {
	this.$root.$$lastDirtyWatch = null;
    //this.$$lastDirtyWatch = null;//原先每次$digest只会置空自己的$$lastDirtyWatch
    this.$beginPhase("$digest");
    ...
};
```
>这是第三次折腾$$lastDirtyWatch这个变量了，前文已经吐槽过这种所谓的‘优化’方式，还想再吐槽一遍。这种没有从本质上降低时间复杂度的‘优化’，却带来了工程上复杂度的提升，到底是不是一个明智的设计？至少目前我认为是愚蠢的。也能看出AngularJs开发者本身对于这种循环脏值检测机制，在工作效率上没有多大信心，所以不惜让代码变得丑陋也要这一点点的优化效果。

## Isolated Scopes
隔离作用域的定义：在作用域树中的构造一个作用域节点，阻止其子节点（包括它本身）访问当前节点的父节点所拥有的属性(隔离了父节点和当前节点)。
>划重点，隔离作用域和原本想象中的不同。
>关键在于，这个隔离作用域依然在作用域树中，而不是一个新的$root。

实现方式为，$new方法新增一个参数isolated，该参数为true是为隔离作用域。
```javascript
Scope.prototype.$new = function(isolated) {
    var child;
    if (isolated) {
        child = new Scope();
    } else {
        var ChildScope = function() {};
        ChildScope.prototype = this;
        child = new ChildScope();
    }
    this.$$children.push(child);
    child.$$watchers = [];
    child.$$children = [];
    return child;
};
```

**探究隔离作用域概念的引入对$digest, $apply, $evalAsync, $applyAsync的影响**
$digest,因为递归的$digest依赖的是每个scope内的$$children变量，而引入隔离作用域并没有与$$children变量相关的改变，所以是ok的。

$apply，我们希望在作用域树中的任意节点调用$apply，会触发整个树的$digest,目前的隔离作用域把$root变量也隔离了，所以在隔离作用域上调用$apply，不会有预期的效果。
解决方法就是，创建隔离作用域的时候加上对$root的引用。
```javascript
Scope.prototype.$new = function(isolated) {
    var child;
    if (isolated) {
        child = new Scope();
        child.$root = this.$root;
    } 
    ...
};
```
对于$evalAsync, $applyAsync而言，$apply的问题只是其中的一部分，$$asyncQueue、$$postDigestQueue、$$applyAsyncQueue、$$applyAsyncId都需要处理。
首先是创建隔离作用域时加入相应的引用
```javascript
Scope.prototype.$new = function(isolated) {
    var child;
    if (isolated) {
        child = new Scope();
        child.$root = this.$root;
        child.$$asyncQueue = this.$$asyncQueue; 
        child.$$postDigestQueue = this.$$postDigestQueue;
        child.$$applyAsyncQueue = this.$$applyAsyncQueue;
    } 
    ...
};
```

涉及变量$$applyAsyncId的地方都改成this.$root.$$applyAsyncId
```javascript
Scope.prototype.$digest = function() {
   ...
   if (this.$root.$$applyAsyncId) {
        clearTimeout(this.$root.$$applyAsyncId);
        this.$$flushApplyAsync();
      }
   }
   ...
```

## Substituting The Parent Scope
先看测试用例，
```javascript
    it('can take some other scope as the parent', function() {
      var prototypeParent = parent.$new();
      var hierarchyParent = parent.$new();
      var child = prototypeParent.$new(false, hierarchyParent);

      prototypeParent.a = 42;
      expect(child.a).toBe(42);

      child.counter = 0;
      child.$watch(function(scope) { 
        scope.counter++;
      });

      prototypeParent.$digest();
      expect(child.counter).toBe(0);

      hierarchyParent.$digest();
      expect(child.counter).toBe(2);
    });
```
Substituting The Parent Scope是指，“我是一个父作用域，我希望我的子作用域只在原型链上和我有继承关系，但是在作用域树上，它是另一个父作用域的子节点”。
实现代码如下，
```javascript
 		Scope.prototype.$new = function(isolated, parent) {
			var child;
			parent = parent || this;
			if (isolated) {
				child = new Scope();
				child.$root = parent.$root;//这里用parent和this是一个效果，用parent显得逻辑更清晰，因为这是隔离作用域的判断分支，这里的this并不希望与child产生联系。
				child.$$asyncQueue = parent.$$asyncQueue;
				child.$$applyAsyncQueue = parent.$$applyAsyncQueue;
				child.$$postDigestQueue = parent.$$postDigestQueue;
			} else {
				var ChildScope = function() { };
				ChildScope.prototype = this;
				child = new ChildScope();
			}
			parent.$$children.push(child);
			child.$$watchers = [];
			child.$$children = [];
			return child;
		};
```
>隔离作用域是屏蔽原型链，保留作用域链
>代理作用域是保留原型链，改变作用域链。

>这又是一个个人认为值得吐槽的设计，"我不知道我的父亲究竟是人还是鬼"，作为子节点还真的是可怜。这种设计将原型链和作用域链原本（基本）统一的概念分开了。再加上上文的隔离作用域概念，极易给使用者造成混淆，这种设计感觉很有问题。

## scope的销毁
AngularJs对scope的销毁操作主要是在scope树中进行的，即删除父scope中$$children内的对应元素。在消除了对该scope对象的引用后，原型链的销毁操作主要由js垃圾回收机制完成。
实现方式是在$new操作时存储父节点的引用，销毁时通过访问$parent，删除$parent.$$children内相应的元素。
```javascript
		Scope.prototype.$new = function(isolated, parent) {
		    ...
			child.$parent = parent;
			return child;
		};
		
		Scope.prototype.$destroy = function() {
			this.$broadcast('$destroy');
			if (this.$parent) {
				var siblings = this.$parent.$$children;
				var indexOfThis = siblings.indexOf(this);
				if (indexOfThis >= 0) {
					siblings.splice(indexOfThis, 1);
				}
			}
			this.$$watchers = null;
		};
```




















