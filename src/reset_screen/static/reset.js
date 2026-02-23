/* === Reset Screen JS === */

/* pywebview Bridge-Variablen */
var _confirmed = false;
var _cancelled = false;
var _startApp = false;
var _closeApp = false;

function onConfirm() {
    _confirmed = true;
    document.getElementById('confirm-box').style.display = 'none';
    document.getElementById('spinner').classList.add('active');
    document.getElementById('subtitle').textContent = 'RESETTING...';
}

function onCancel() {
    _cancelled = true;
    document.getElementById('confirm-box').style.display = 'none';
    document.getElementById('subtitle').textContent = 'ABGEBROCHEN';
}

function onStart() {
    _startApp = true;
}

function onClose() {
    _closeApp = true;
}

function isConfirmed() {
    return _confirmed;
}

function isCancelled() {
    return _cancelled;
}

function shouldStartApp() {
    return _startApp;
}

function shouldCloseApp() {
    return _closeApp;
}

function showFinishButtons() {
    document.getElementById('spinner').classList.remove('active');
    document.getElementById('subtitle').textContent = 'RESET COMPLETE';
    document.getElementById('finish-buttons').style.display = 'flex';
}

/* === Typewriter Engine (wie splash_screen) === */

function addLog(text) {
    var wrapper = document.getElementById('console-wrapper');
    var line = document.createElement('div');
    line.className = 'log-line';
    if (text.indexOf('WARNUNG') !== -1 || text.indexOf('WARN') !== -1) {
        line.classList.add('warn');
    } else if (text.indexOf('ERROR') !== -1 || text.indexOf('FEHLER') !== -1) {
        line.classList.add('error');
    } else if (text.indexOf('OK') !== -1 || text.indexOf('bereit') !== -1 || text.indexOf('erfolgreich') !== -1) {
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
