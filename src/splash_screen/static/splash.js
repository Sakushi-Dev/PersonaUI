function addLog(text) {
    var wrapper = document.getElementById('console-wrapper');
    var line = document.createElement('div');
    line.className = 'log-line';
    if (text.indexOf('WARNING') !== -1 || text.indexOf('WARN') !== -1) {
        line.classList.add('warn');
    } else if (text.indexOf('ERROR') !== -1 || text.indexOf('error') !== -1) {
        line.classList.add('error');
    } else if (text.indexOf('running') !== -1 || text.indexOf('ready') !== -1 || text.indexOf('Ready') !== -1) {
        line.classList.add('info');
    } else {
        line.classList.add('default');
    }
    line.textContent = text;
    wrapper.appendChild(line);
    wrapper.scrollTop = wrapper.scrollHeight;
}

var _typeQueue = [];
var _typing = false;

function typeLine(text, cls) {
    _typeQueue.push({text: text, cls: cls || 'default', bar: false});
    if (!_typing) _processQueue();
}

function typeLineWithBar(text, cls, duration) {
    _typeQueue.push({text: text, cls: cls || 'default', bar: true, duration: duration || 1500});
    if (!_typing) _processQueue();
}

function _processQueue() {
    if (_typeQueue.length === 0) { _typing = false; return; }
    _typing = true;
    var item = _typeQueue.shift();
    var wrapper = document.getElementById('console-wrapper');
    var line = document.createElement('div');
    line.className = 'log-line ' + item.cls;
    var textSpan = document.createElement('span');
    line.appendChild(textSpan);
    wrapper.appendChild(line);
    var i = 0;
    var speed = 18;
    function tick() {
        if (i < item.text.length) {
            textSpan.textContent += item.text.charAt(i);
            i++;
            wrapper.scrollTop = wrapper.scrollHeight;
            setTimeout(tick, speed);
        } else if (item.bar) {
            var barWrap = document.createElement('span');
            barWrap.className = 'progress-bar';
            var fill = document.createElement('span');
            fill.className = 'progress-fill';
            barWrap.appendChild(fill);
            line.appendChild(barWrap);
            wrapper.scrollTop = wrapper.scrollHeight;
            var start = Date.now();
            function animBar() {
                var pct = Math.min(100, ((Date.now() - start) / item.duration) * 100);
                fill.style.width = pct + '%';
                if (pct < 100) { requestAnimationFrame(animBar); }
                else { setTimeout(_processQueue, 80); }
            }
            animBar();
        } else {
            setTimeout(_processQueue, 80);
        }
    }
    tick();
}
