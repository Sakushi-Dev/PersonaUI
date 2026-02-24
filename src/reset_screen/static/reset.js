/* === Reset Screen JS === */

/* ─── State ─── */
var _confirmed = false;
var _cancelled = false;
var _startApp = false;
var _closeApp = false;

var _selectedPreset = null;
var _selectedPersonas = [];

/* Presets & Personas are injected from Python (window._PRESETS, window._PRESET_ORDER, window._PERSONAS) */

/* ─── pywebview Bridge ─── */

function isConfirmed()    { return _confirmed; }
function isCancelled()    { return _cancelled; }
function shouldStartApp() { return _startApp; }
function shouldCloseApp() { return _closeApp; }

function getSelectedPreset()   { return _selectedPreset; }
function getSelectedPersonas() { return JSON.stringify(_selectedPersonas); }

function showFinishButtons() {
    document.getElementById('spinner').classList.remove('active');
    document.getElementById('subtitle').textContent = 'RESET COMPLETE';
    document.getElementById('finish-buttons').style.display = 'flex';
}

/* ─── Badge mapping per preset ─── */

var PRESET_BADGES = {
    'full':            { text: 'ALL', cls: 'badge-danger' },
    'keep_api':        { text: 'SAFE', cls: 'badge-warn' },
    'chat_only':       { text: 'CHATS', cls: 'badge-safe' },
    'personas_select': { text: 'SELECT', cls: 'badge-warn' },
    'settings_only':   { text: 'SETTINGS', cls: 'badge-safe' },
    'prompts_only':    { text: 'PROMPTS', cls: 'badge-safe' },
    'troubleshoot':    { text: 'FIX', cls: 'badge-safe' }
};

/* ─── Rendering ─── */

function renderPresets() {
    var list = document.getElementById('preset-list');
    list.innerHTML = '';

    var order = window._PRESET_ORDER || [];
    var presets = window._PRESETS || {};

    for (var i = 0; i < order.length; i++) {
        var pid = order[i];
        var p = presets[pid];
        if (!p) continue;

        var card = document.createElement('div');
        card.className = 'preset-card' + (pid === 'full' ? ' danger' : '');
        card.setAttribute('data-pid', pid);
        card.onclick = (function(id) { return function() { selectPreset(id); }; })(pid);

        var radio = document.createElement('div');
        radio.className = 'preset-radio';

        var info = document.createElement('div');
        info.className = 'preset-info';

        var name = document.createElement('div');
        name.className = 'preset-name';
        name.textContent = p.name;

        var desc = document.createElement('div');
        desc.className = 'preset-desc';
        desc.textContent = p.desc;

        info.appendChild(name);
        info.appendChild(desc);

        var badge = document.createElement('span');
        var bdata = PRESET_BADGES[pid] || { text: '', cls: 'badge-safe' };
        badge.className = 'preset-badge ' + bdata.cls;
        badge.textContent = bdata.text;

        card.appendChild(radio);
        card.appendChild(info);
        card.appendChild(badge);
        list.appendChild(card);
    }
}

function renderPersonas() {
    var list = document.getElementById('persona-list');
    list.innerHTML = '';

    var personas = window._PERSONAS || [];

    for (var i = 0; i < personas.length; i++) {
        var p = personas[i];

        var item = document.createElement('div');
        item.className = 'persona-item';
        item.setAttribute('data-pid', p.id);
        item.onclick = (function(id) { return function() { togglePersona(id); }; })(p.id);

        var check = document.createElement('div');
        check.className = 'persona-check';

        var nameEl = document.createElement('span');
        nameEl.className = 'persona-name';
        nameEl.textContent = p.name + (p.id !== 'default' ? '  (' + p.id.substring(0, 8) + '...)' : '');

        item.appendChild(check);
        item.appendChild(nameEl);

        if (p.is_default) {
            var tag = document.createElement('span');
            tag.className = 'persona-tag tag-default';
            tag.textContent = 'Default';
            item.appendChild(tag);
        }
        if (p.is_active) {
            var tagA = document.createElement('span');
            tagA.className = 'persona-tag tag-active';
            tagA.textContent = 'Active';
            item.appendChild(tagA);
        }

        list.appendChild(item);
    }
}

/* ─── Selection Logic ─── */

function selectPreset(pid) {
    _selectedPreset = pid;

    /* Update radio visuals */
    var cards = document.querySelectorAll('.preset-card');
    for (var i = 0; i < cards.length; i++) {
        cards[i].classList.remove('selected');
    }
    var sel = document.querySelector('.preset-card[data-pid="' + pid + '"]');
    if (sel) sel.classList.add('selected');

    /* Show/hide persona select box */
    var pbox = document.getElementById('persona-select-box');
    if (pid === 'personas_select') {
        pbox.style.display = 'block';
    } else {
        pbox.style.display = 'none';
        _selectedPersonas = [];
        /* Uncheck all personas */
        var items = document.querySelectorAll('.persona-item');
        for (var j = 0; j < items.length; j++) {
            items[j].classList.remove('checked');
        }
    }

    updateNextButton();
}

function togglePersona(pid) {
    var idx = _selectedPersonas.indexOf(pid);
    if (idx >= 0) {
        _selectedPersonas.splice(idx, 1);
    } else {
        _selectedPersonas.push(pid);
    }

    /* Update visual */
    var item = document.querySelector('.persona-item[data-pid="' + pid + '"]');
    if (item) {
        item.classList.toggle('checked');
    }

    updateNextButton();
}

function updateNextButton() {
    var btn = document.getElementById('btn-preset-next');
    if (!_selectedPreset) {
        btn.disabled = true;
        return;
    }
    if (_selectedPreset === 'personas_select' && _selectedPersonas.length === 0) {
        btn.disabled = true;
        return;
    }
    btn.disabled = false;
}

/* ─── Phase Navigation ─── */

function onPresetNext() {
    if (!_selectedPreset) return;

    var presets = window._PRESETS || {};
    var preset = presets[_selectedPreset];
    if (!preset) return;

    /* Fill confirm text */
    document.getElementById('confirm-preset-name').textContent = preset.name;

    var detail = preset.desc;
    if (_selectedPreset === 'personas_select' && _selectedPersonas.length > 0) {
        var personas = window._PERSONAS || [];
        var names = [];
        for (var i = 0; i < _selectedPersonas.length; i++) {
            for (var j = 0; j < personas.length; j++) {
                if (personas[j].id === _selectedPersonas[i]) {
                    names.push(personas[j].name);
                    break;
                }
            }
        }
        detail += '\n\nPersonas to delete: ' + names.join(', ');
    }
    document.getElementById('confirm-detail').textContent = detail;

    /* Switch phases */
    document.getElementById('preset-box').style.display = 'none';
    document.getElementById('confirm-box').style.display = 'block';
}

function onBack() {
    document.getElementById('confirm-box').style.display = 'none';
    document.getElementById('preset-box').style.display = 'block';
}

function onConfirm() {
    _confirmed = true;
    document.getElementById('confirm-box').style.display = 'none';
    document.getElementById('spinner').classList.add('active');
    document.getElementById('subtitle').textContent = 'RESETTING...';
}

function onCancel() {
    _cancelled = true;
    document.getElementById('preset-box').style.display = 'none';
    document.getElementById('subtitle').textContent = 'CANCELLED';
}

function onStart() { _startApp = true; }
function onClose() { _closeApp = true; }

/* ─── Init (called from Python after data injection) ─── */

function initResetUI() {
    renderPresets();
    renderPersonas();
}

/* ─── Typewriter Engine ─── */

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
