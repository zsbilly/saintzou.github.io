# Build Your Own Angular阅读笔记(Scope Event)
本章主要介绍了对$scope中的事件传递机制的实现。与jquery的事件机制最本质的区别是AngularJs的事件传递依赖scope树。相关的方法有三个：$on（监听）,$broadcast（向下传递）,$emit（向上传递）。实现方式为发布者/订阅者的模式，与$watch的机制类似。
## $on
$on的作用是注册事件的监听。
首先在scope下创建属性$$listeners，存放监听器。
```javascript
function Scope() {
    ...
    this.$$listeners = {};
};
```
$$listeners是一个形如{'event1':[listener1,...],'event2':[listener2,...]}这样的数据结构。其中的event表示监听事件的名称，其对应的值为监听该事件的回调函数队列。
方法$on的实现如下,
```javascript
Scope.prototype.$on = function(eventName, listener) { 
    var listeners = this.$$listeners[eventName];
    if (!listeners) {
        this.$$listeners[eventName] = listeners = []; 
        }
    listeners.push(listener);
};
```
当然，每个scope都应当拥有自己的$$listener，而不是父scope的$$listener的引用（隔离作用域也要考虑在内),所以在new一个scope的时候需要创建一个新的$$listener。

```javascript
Scope.prototype.$new = function(isolated, parent) {
    ...
    if (isolated) {
        ...
    } else {
        var ChildScope = function() { }; 
        ChildScope.prototype = this; 
        child = new ChildScope();
        }
    child.$$listeners = {};
    ...
}
```

## $emit和$broadcast的简单实现
所谓简单实现是指，实现$emit,$broadcast中除**事件传递**以外的功能。
首先实现一个$$fireEventOnScope方法，功能是触发当前scope下的$$listeners[eventName]
```javascript
Scope.prototype.$$fireEventOnScope = function(eventName) { 
    var listeners = this.$$listeners[eventName] || [];
     _.forEach(listeners, function(listener) {
        listener();
    });
};
```

暂时将$emit和$broadcast实现为调用$$fireEventOnScope
```javascript
Scope.prototype.$emit = function(eventName) {
    this.$$fireEventOnScope(eventName); 
};
Scope.prototype.$broadcast = function(eventName) {
    this.$$fireEventOnScope(eventName); 
};
```
原书注：AngualrJS的实现里并没有$$fireEventOnScope方法，只是单纯的将该功能在$emit和$broadcast中实现两遍。

## 与listener有关的扩展
listener回调需要知道自己是被哪个事件触发的，所以需要构造一个event对象并将其传递给listener方法。
```javascript
Scope.prototype.$$fireEventOnScope = function(eventName) { 
    var event = {name: eventName};
    var listeners = this.$$listeners[eventName] || [];
     _.forEach(listeners, function(listener) {
        listener(event);
    });
};
```

光有eventName还不行，事件的发布者需要向订阅者传递参数。就像这样，(传递多个参数的情形，采用扩充$emit/$broadcast方法的参数个数的方式)
```javascript
aScope.$emit('eventName' ,  'and' ,  'additional' ,  'arguments' );
```
实现如下，
```javascript
Scope.prototype.$emit = function(eventName) { 
    var event = {name: eventName};
    var listenerArgs = [event].concat(additionalArgs);
    var additionalArgs = _.rest(arguments);
    this.$$fireEventOnScope(eventName, additionalArgs); 
    return  event;
};
Scope.prototype.$broadcast = function(eventName) { 
    var event = {name: eventName};
    var listenerArgs = [event].concat(additionalArgs);
    var additionalArgs = _.rest(arguments);
    this.$$fireEventOnScope(eventName, additionalArgs); 
    return  event;
};

Scope.prototype.$$fireEventOnScope = function(eventName,additionalArgs) { 
    var listeners = this.$$listeners[eventName] || [];
     _.forEach(listeners, function(listener) {
        listener.apply(null, listenerArgs);
    });
};
```
用默认参数arguments获取到除第一个参数外的所有参数，并传给$$fireEventOnScope。
$emit/$broadcast均返回一个在其方法内构建的event对象。

注销listener。类似$watch的处理方式，$on方法返回一个销毁自身（监听器）的方法，实现如下，
```javascript
Scope.prototype.$on = function(eventName, listener) { 
    var listeners = this.$$listeners[eventName];
    if (!listeners) {
        this.$$listeners[eventName] = listeners = []; 
        }
    listeners.push(listener);
    return function() {
        var index = listeners.indexOf(listener);
        if (index >= 0) {
            //listeners.splice(index, 1);
            listeners[index] = null; 
        }

    };
};
```
注意，不可采用注释中的代码实现，因为当listener在被调用时正处于listeners队列迭代的过程中，此时直接删除listeners中的元素会导致迭代过程发生错误（被删除元素的下一个元素被跳过）。测试用例如下,
```javascript
//method==$emit || $broadcast
it('does not skip the next listener when removed on '+method, function() {
        var deregister;

        var listener = function() {
          deregister();
        };
        var nextListener = jasmine.createSpy();

        deregister = scope.$on('someEvent', listener);
        scope.$on('someEvent', nextListener);

        scope[method]('someEvent');

        expect(nextListener).toHaveBeenCalled();
});
```

既然listeners队列中可能出现null，就需要对$$fireEventOnScope作出修正。
```javascript
Scope.prototype.$$fireEventOnScope = function(eventName,additionalArgs) { 
    var listeners = this.$$listeners[eventName] || [];
    var i = 0;
    while (i < listeners.length) {
        if (listeners[i] === null) { 
            listeners.splice(i, 1);
        } else {
            listeners[i].apply(null, listenerArgs);
            i++; 
        }
    }
};
```

## 事件的传递
对$emit进行改造
```javascript
Scope.prototype.$emit = function (eventName) {
    ...
    var additionalArgs = _.rest(arguments);
    var scope = this;
    do {
        scope.$$fireEventOnScope(eventName, additionalArgs);
        scope = scope.$parent;
    } while (scope);
};
```
对$broadcast进行改造
```javascript
Scope.prototype.$broadcast = function (eventName) {
    var event = {name: eventName};
    var listenerArgs = [event].concat(_.rest(arguments));
    this.$$everyScope(function (scope) {
        scope.$$fireEventOnScope(eventName, listenerArgs);
        return true;
    });
    return event;
};
```
**显然$broadcast的开销比$emit的开销大。**

在event对象中加入targetScope与currentScope这两个属性。
targetScope用来标记事件实际发生在哪个scope上，currentScope表示当前正在处理该事件的listener所属的scope。测试用例如下，
```javascript
    //$emit与此类似
    it('attaches currentScope on $broadcast', function() {
      var currentScopeOnScope, currentScopeOnChild;
      var scopeListener = function(event) {
        currentScopeOnScope = event.currentScope;
      };
      var childListener = function(event) {
        currentScopeOnChild = event.currentScope;
      };
      scope.$on('someEvent', scopeListener);
      child.$on('someEvent', childListener);

      scope.$broadcast('someEvent');

      expect(currentScopeOnScope).toBe(scope);
      expect(currentScopeOnChild).toBe(child);
    });
```

实现如下，在事件被处理以后也别忘了将currentScope置null。
```javascript
Scope.prototype.$emit = function (eventName) {
    var event = {name: eventName, targetScope: this};
    var listenerArgs = [event].concat(_.rest(arguments));
    ...
    do {
        event.currentScope = scope;
        scope.$$fireEventOnScope(eventName, listenerArgs);
        scope = scope.$parent;
    } while (scope);
    event.currentScope = null;
    return event;
};

 Scope.prototype.$broadcast = function (eventName) {
    var event = {name: eventName, targetScope: this};
    var listenerArgs = [event].concat(_.rest(arguments));
    ...
    this.$$everyScope(function (scope) {
        event.currentScope = scope;
        scope.$$fireEventOnScope(eventName, listenerArgs);
        return true;
    });
    event.currentScope = null;
    return event;
};
```
> var listenerArgs = [event].concat(_.rest(arguments));因为event作为数组里的一个对象，本身在数组中存放的是其引用值，即listenerArgs[0]===event，在此特别强调。

stopPropagation,阻止事件继续传递的功能**只在$emit中有效**,实现如下，
```javascript
Scope.prototype.$emit = function (eventName) {
    var propagationStopped = false;
    var event = {
        name: eventName, 
        targetScope: this, 
        stopPropagation: function () {
            propagationStopped = true;
        }
    };
    var listenerArgs = [event].concat(_.rest(arguments));
    var scope = this;
    do {
        event.currentScope = scope;
        scope.$$fireEventOnScope(eventName, listenerArgs);
        scope = scope.$parent;
    } while (scope && !propagationStopped);
    return event;
};
```

preventDefault，该功能出现在AngularJS里其实有些奇怪，这东西在DOM事件中原本是用来屏蔽掉某些浏览器默认的事件处理行为（比如让超链接的点击事件不触发跳转，但是事件本身依然会传递下去），然而目前在AngularJS里Scope并没有“默认行为”。原书中提到了后面的章节中$locationService的实现与此有关。
实现方式与stopPropagation类似，
```javascript
Scope.prototype.$emit = function (eventName) {
    var propagationStopped = false;
    var event = {
        name: eventName, 
        targetScope: this, 
        stopPropagation: function () {
            propagationStopped = true;
        },
        preventDefault: function() {
            event.defaultPrevented = true; 
        }
    };
    ...
    return event;
};

//$broadcast同理
```

scope被删除时，需要向下广播它被删除的消息,同时也要把$$listeners清空
```javascript
Scope.prototype.$destroy = function() {
     this.$broadcast( $destroy );
     ...
     this.$$listeners = {};
};
```

异常处理。与$evalAsync类似，都是在执行外部传入的回调函数的地方包裹一层try...catch
```javascript
Scope.prototype.$$fireEventOnScope = function (eventName, listenerArgs) {
    var listeners = this.$$listeners[eventName] || [];
    var i = 0;
    while (i < listeners.length) {
        if (listeners[i] === null) {
            listeners.splice(i, 1);
        } else {
            try {
                listeners[i].apply(null, listenerArgs);
            } catch (e) {
                console.error(e);
            }
            i++;
        }
    }
};
```


























