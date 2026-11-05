/* ==========================================================================
   课程信息管理 · 页面交互
   纯原生 JS，无任何依赖。功能：
     1. 表格即时搜索（data-table-filter）
     2. 侧边栏滚动高亮（data-spy）
     3. 表格横向溢出提示（配合右侧固定的操作列）
     4. 删除前二次确认（data-confirm）
     5. 顶部提示条自动淡出
     6. 日期字段默认填今天（data-default-today）
     7. 按 "/" 快速聚焦搜索框
   ========================================================================== */
(function () {
    'use strict';

    /* ------------------------------------------------------------------
       1. 表格即时搜索
       用法：<input data-table-filter="teacher-table">
             <table id="teacher-table">
       ------------------------------------------------------------------ */
    function initTableFilters() {
        var inputs = document.querySelectorAll('[data-table-filter]');

        Array.prototype.forEach.call(inputs, function (input) {
            var table = document.getElementById(input.getAttribute('data-table-filter'));
            if (!table || !table.tBodies.length || !table.tHead) {
                return;
            }

            var tbody = table.tBodies[0];
            var columns = table.tHead.rows[0].cells.length;
            var rows = Array.prototype.filter.call(tbody.rows, function (row) {
                return !row.classList.contains('empty') && !row.classList.contains('no-match');
            });

            // 表里本来就没数据，就不用做搜索了
            if (!rows.length) {
                return;
            }

            // 准备一行"查无结果"
            var noMatch = document.createElement('tr');
            noMatch.className = 'no-match';
            noMatch.style.display = 'none';
            var cell = document.createElement('td');
            cell.colSpan = columns;
            cell.textContent = '没有找到匹配的记录';
            noMatch.appendChild(cell);
            tbody.appendChild(noMatch);

            function apply() {
                var keyword = input.value.trim().toLowerCase();
                var shown = 0;

                rows.forEach(function (row) {
                    var text = (row.textContent || '').toLowerCase();
                    var hit = !keyword || text.indexOf(keyword) !== -1;
                    row.style.display = hit ? '' : 'none';
                    if (hit) {
                        shown++;
                    }
                });

                noMatch.style.display = shown ? 'none' : '';
            }

            input.addEventListener('input', apply);

            // 搜索框里按 Esc 清空
            input.addEventListener('keydown', function (event) {
                if (event.key === 'Escape') {
                    input.value = '';
                    apply();
                }
            });
        });
    }

    /* ------------------------------------------------------------------
       2. 侧边栏滚动高亮
       主页是三段式（概览 / 讲师 / 课程 / 学生），滚动到哪一块就点亮哪一项。
       没有这些锚点的页面（表单页）直接跳过。
       ------------------------------------------------------------------ */
    function initScrollSpy() {
        var links = document.querySelectorAll('[data-spy]');
        if (!links.length) {
            return;
        }

        var items = [];
        Array.prototype.forEach.call(links, function (link) {
            var section = document.getElementById(link.getAttribute('data-spy'));
            if (section) {
                items.push({ link: link, section: section });
            }
        });

        if (!items.length) {
            return;
        }

        function setActive(target) {
            Array.prototype.forEach.call(links, function (link) {
                link.classList.toggle('is-active', link === target);
            });
        }

        function update() {
            var topbar = document.querySelector('.topbar');
            var offset = (topbar ? topbar.offsetHeight : 0) + 96;
            var current = items[0];

            items.forEach(function (item) {
                if (item.section.getBoundingClientRect().top <= offset) {
                    current = item;
                }
            });

            setActive(current.link);
        }

        var ticking = false;
        function onScroll() {
            if (ticking) {
                return;
            }
            ticking = true;
            window.requestAnimationFrame(function () {
                ticking = false;
                update();
            });
        }

        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', update);
        update();
    }

    /* ------------------------------------------------------------------
       3. 表格溢出提示
       操作列是 position: sticky 钉在右侧的，只有当表格真的横向溢出时
       才给它加左侧阴影，宽屏下保持干净。
       ------------------------------------------------------------------ */
    function initScrollShadows() {
        var wraps = document.querySelectorAll('.table-wrap');
        if (!wraps.length) {
            return;
        }

        function sync(wrap) {
            wrap.classList.toggle('is-scrollable', wrap.scrollWidth > wrap.clientWidth + 1);
        }

        function syncAll() {
            Array.prototype.forEach.call(wraps, sync);
        }

        syncAll();
        window.addEventListener('resize', syncAll);
    }

    /* ------------------------------------------------------------------
       4. 删除前二次确认
       用法：<form method="post" data-confirm="确定要删除吗？">
       为什么不用 onsubmit="return confirm('...')"：
       姓名/昵称是用户填的，只要里面带一个单引号，整段内联 JS 就语法错误，
       按钮会「点了没反应」或者直接不弹确认就提交。这里把它变成属性值读出来，
       无论内容是引号还是尖括号都不会破坏脚本。
       ------------------------------------------------------------------ */
    function initConfirmForms() {
        var forms = document.querySelectorAll('form[data-confirm]');

        Array.prototype.forEach.call(forms, function (form) {
            form.addEventListener('submit', function (event) {
                if (!window.confirm(form.getAttribute('data-confirm') || '确定执行该操作吗？')) {
                    event.preventDefault();
                    return;
                }

                // 确认后锁住按钮，避免手抖连点造成重复提交
                var button = form.querySelector('button[type="submit"]');
                if (button) {
                    button.disabled = true;
                }
            });
        });
    }

    /* ------------------------------------------------------------------
       5. 提示条自动淡出
       ------------------------------------------------------------------ */
    function initFlashes() {
        var flashes = document.querySelectorAll('.flash');

        Array.prototype.forEach.call(flashes, function (flash) {
            setTimeout(function () {
                flash.classList.add('is-hiding');
                setTimeout(function () {
                    if (flash.parentNode) {
                        flash.parentNode.removeChild(flash);
                    }
                }, 320);
            }, 6000);
        });
    }

    /* ------------------------------------------------------------------
       6. 日期字段默认填今天（只在字段为空时生效）
       ------------------------------------------------------------------ */
    function initDefaultDates() {
        var fields = document.querySelectorAll('[data-default-today]');
        if (!fields.length) {
            return;
        }

        var now = new Date();
        var today = now.getFullYear() + '-' +
            String(now.getMonth() + 1).padStart(2, '0') + '-' +
            String(now.getDate()).padStart(2, '0');

        Array.prototype.forEach.call(fields, function (field) {
            if (!field.value) {
                field.value = today;
            }
        });
    }

    /* ------------------------------------------------------------------
       7. 按 "/" 聚焦到第一个搜索框
       ------------------------------------------------------------------ */
    function initSlashShortcut() {
        document.addEventListener('keydown', function (event) {
            if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) {
                return;
            }

            var tag = (event.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea' || tag === 'select') {
                return;
            }

            var search = document.querySelector('[data-table-filter]');
            if (!search) {
                return;
            }

            event.preventDefault();
            search.focus();
        });
    }

    /* ------------------------------------------------------------------
       启动
       ------------------------------------------------------------------ */
    function boot() {
        initTableFilters();
        initScrollSpy();
        initScrollShadows();
        initConfirmForms();
        initFlashes();
        initDefaultDates();
        initSlashShortcut();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
