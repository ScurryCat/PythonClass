(() => {
    'use strict';

    async function postForm(url, form, values) {
        const data = new FormData();
        data.set('csrfmiddlewaretoken', form.elements.csrfmiddlewaretoken.value);
        for (const [key, value] of Object.entries(values)) {
            data.set(key, value);
        }

        let response;
        try {
            response = await fetch(url, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
                body: data,
            });
        } catch {
            throw new Error('网络连接失败，请重试。');
        }

        if (response.redirected) {
            throw new Error('登录已过期，请刷新页面后重新登录。');
        }
        const payload = await response.json().catch(() => null);
        if (!response.ok || !payload) {
            throw new Error(payload?.error || '请求失败，请刷新页面后重试。');
        }
        return payload;
    }

    function showStatus(status, message, isError = false) {
        status.textContent = message;
        status.dataset.error = String(isError);
    }

    async function runRequest(button, status, loadingMessage, execute) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        showStatus(status, loadingMessage);
        try {
            await execute();
        } catch (error) {
            showStatus(status, error.message, true);
        } finally {
            button.removeAttribute('aria-busy');
            button.disabled = false;
        }
    }

    function initProgress(root) {
        const buttons = [...root.querySelectorAll('[data-filter]')];
        const rows = [...root.querySelectorAll('[data-row-status]')];
        const count = root.querySelector('[data-roster-count]');
        const empty = root.querySelector('[data-roster-empty]');

        for (const button of buttons) {
            button.addEventListener('click', () => {
                const filter = button.dataset.filter;
                let visible = 0;
                for (const row of rows) {
                    row.hidden = filter !== 'all' && row.dataset.rowStatus !== filter;
                    if (!row.hidden) {
                        visible++;
                    }
                }
                for (const item of buttons) {
                    item.setAttribute('aria-pressed', String(item === button));
                }
                count.textContent = `显示 ${visible} 名学生`;
                empty.hidden = visible !== 0;
            });
        }
    }

    function initOcr(form) {
        const fileInput = form.querySelector('[data-screenshot-file]');
        const textInput = form.elements.recognized_text;
        const preview = form.querySelector('[data-screenshot-preview]');
        const button = form.querySelector('[data-ocr-button]');
        const status = form.querySelector('[data-ocr-status]');
        let previewUrl;
        let revision = 0;

        fileInput.addEventListener('change', () => {
            revision++;
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
                previewUrl = null;
            }

            const file = fileInput.files[0];
            button.disabled = !file || button.hasAttribute('aria-busy');
            if (file && ['image/png', 'image/jpeg'].includes(file.type)) {
                previewUrl = URL.createObjectURL(file);
                preview.src = previewUrl;
                preview.hidden = false;
            } else {
                preview.removeAttribute('src');
                preview.hidden = true;
            }
            if (!button.hasAttribute('aria-busy')) {
                showStatus(status, '');
            }
        });
        textInput.addEventListener('input', () => {
            revision++;
        });
        preview.addEventListener('error', () => {
            preview.hidden = true;
        });

        button.addEventListener('click', async () => {
            const file = fileInput.files[0];
            if (!file) {
                return;
            }
            const requestRevision = revision;
            await runRequest(button, status, '正在识别截图文字…', async () => {
                const result = await postForm(form.dataset.ocrUrl, form, { image: file });
                if (requestRevision !== revision) {
                    showStatus(status, '图片或文字已修改。需要时可重新识别。');
                    return;
                }
                if (!result.text) {
                    showStatus(status, '未识别到文字。可以换一张截图或手工录入。');
                    return;
                }
                textInput.value = result.text;
                textInput.dispatchEvent(new Event('input', { bubbles: true }));
                showStatus(status, '已填入识别结果，提交前可以校对。');
            });
            button.disabled = !fileInput.files.length;
        });
    }

    function renderResource(resource) {
        const article = document.createElement('article');
        article.className = 'study-resource';

        const heading = document.createElement('h3');
        // 校验展示链接的协议，避免执行来自数据的 URL。
        if (/^https?:\/\//i.test(resource.url)) {
            const link = document.createElement('a');
            link.href = resource.url;
            link.textContent = resource.title;
            heading.append(link);
        } else {
            heading.textContent = resource.title;
        }

        const description = document.createElement('p');
        description.textContent = resource.description;
        const reason = document.createElement('p');
        reason.className = 'hint';
        reason.textContent = resource.reason;
        article.append(heading, description, reason);
        return article;
    }

    function initRecommendations(root, source) {
        const form = root.querySelector('[data-recommend-form]');
        const button = form.querySelector('[data-recommend-button]');
        const status = root.querySelector('[data-recommend-status]');
        const output = root.querySelector('[data-recommend-results]');
        const keywordBox = root.querySelector('[data-keyword-box]');
        const keywords = root.querySelector('[data-keywords]');
        const resources = root.querySelector('[data-resources]');
        const inputs = [source.elements.recognized_text, source.elements.difficulties];
        let revision = 0;

        for (const input of inputs) {
            input.addEventListener('input', () => {
                revision++;
                if (!output.hidden) {
                    output.hidden = true;
                    showStatus(status, '内容已修改，可重新推荐资料。');
                }
            });
        }

        button.addEventListener('click', () => {
            const query = Object.fromEntries(inputs.map(input => [input.name, input.value]));
            const requestRevision = revision;
            output.hidden = true;
            runRequest(button, status, '正在匹配学习资料…', async () => {
                const result = await postForm(form.dataset.recommendUrl, form, query);
                if (requestRevision !== revision) {
                    showStatus(status, '内容已修改，请重新推荐资料。');
                    return;
                }

                keywords.replaceChildren(...result.keywords.map(word => {
                    const item = document.createElement('li');
                    item.textContent = word;
                    return item;
                }));
                keywordBox.hidden = !result.keywords.length;
                resources.replaceChildren(...result.resources.map(renderResource));
                output.hidden = !result.keywords.length && !result.resources.length;
                showStatus(status, result.resources.length
                    ? `找到 ${result.resources.length} 条匹配资料。`
                    : '没有匹配的资料，可以补充疑难点后重试。');
            });
        });
    }

    function initDraft(form) {
        const button = form.querySelector('[data-draft-button]');
        const status = form.querySelector('[data-draft-status]');
        const resultPanel = form.querySelector('[data-draft-result]');
        const output = form.querySelector('[data-draft-output]');
        const useDraft = form.querySelector('[data-use-draft]');
        const points = form.elements.review_points;
        const feedback = form.elements.feedback;
        let revision = 0;

        function updateUseLabel() {
            useDraft.textContent = feedback.value.trim() ? '用草稿替换反馈' : '填入反馈';
        }

        updateUseLabel();
        feedback.addEventListener('input', updateUseLabel);
        points.addEventListener('input', () => {
            revision++;
            if (!resultPanel.hidden) {
                resultPanel.hidden = true;
                showStatus(status, '批阅要点已修改，可重新生成草稿。');
            }
        });

        button.addEventListener('click', () => {
            const reviewPoints = points.value.trim();
            if (!reviewPoints) {
                showStatus(status, '填写批阅要点后即可生成草稿。', true);
                points.focus();
                return;
            }
            const requestRevision = revision;
            resultPanel.hidden = true;
            runRequest(button, status, '正在生成评语草稿…', async () => {
                const result = await postForm(form.dataset.draftUrl, form, { review_points: reviewPoints });
                if (requestRevision !== revision) {
                    showStatus(status, '批阅要点已修改，请重新生成草稿。');
                    return;
                }
                output.textContent = result.draft;
                resultPanel.hidden = false;
                showStatus(status, '草稿已生成。核对后可填入反馈。');
            });
        });

        useDraft.addEventListener('click', () => {
            feedback.value = output.textContent;
            updateUseLabel();
            feedback.focus();
            showStatus(status, '已填入反馈，可以继续编辑。');
        });
    }

    const progress = document.querySelector('[data-progress]');
    const task = document.querySelector('[data-study-task]');
    const review = document.querySelector('[data-review-form]');
    if (progress) {
        initProgress(progress);
    }
    if (task) {
        const submission = task.querySelector('[data-submission-form]');
        if (submission) {
            initOcr(submission);
        }
        initRecommendations(task, submission || task.querySelector('[data-recommend-form]'));
    }
    if (review) {
        initDraft(review);
    }
})();
