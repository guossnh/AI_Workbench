// 初始化所有tooltip提示
const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
tooltips.forEach(tooltip => {
    new bootstrap.Tooltip(tooltip);
});

// 全局扩词开关状态处理
const usePreLlmSwitch = document.getElementById('usePreLlmSwitch');
if (usePreLlmSwitch) {
    // 从localStorage读取之前的开关状态
    const savedState = localStorage.getItem('usePreLlm');
    if (savedState !== null) {
        usePreLlmSwitch.checked = savedState === 'true';
    }

    // 监听开关状态变化
    usePreLlmSwitch.addEventListener('change', function() {
        // 保存开关状态到localStorage
        localStorage.setItem('usePreLlm', this.checked);
    });
}

// 生成图片时获取开关状态
function generateImage(prompt) {
    const loading = document.getElementById('loading');
    const imagePreview = document.getElementById('imagePreview');
    
    // 显示加载动画
    loading.style.display = 'block';
    imagePreview.querySelectorAll('img').forEach(img => img.remove());

    // 获取开关状态
    const usePreLlm = usePreLlmSwitch ? usePreLlmSwitch.checked : true;

    // 发送API请求
    fetch('/api/generate-images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: prompt,
            usePreLlm: usePreLlm
        })
    })
    .then(response => response.json())
    .then(data => {
        // 隐藏加载动画
        loading.style.display = 'none';

        if (data.success) {
            // 清除提示文本
            imagePreview.querySelector('.text-muted')?.remove();
            
            // 显示生成的图片
            data.images.forEach(imagePath => {
                const img = document.createElement('img');
                img.src = imagePath;
                img.className = 'mb-3';
                imagePreview.appendChild(img);
            });
        } else {
            alert(data.error || '生成图片失败');
        }
    })
    .catch(error => {
        loading.style.display = 'none';
        alert('生成图片失败：' + error.message);
    });
}

// 加载文件列表
function loadFileList() {
    fetch('/api/files')
        .then(response => response.json())
        .then(files => {
            const fileList = document.getElementById('fileList');
            if (fileList) {
                fileList.innerHTML = files.map(file => `
                    <a href="#" class="list-group-item list-group-item-action" data-file="${file}">
                        ${file.replace('.csv', '')}
                    </a>
                `).join('');

                // 添加点击事件监听
                fileList.querySelectorAll('a').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        loadFileContent(this.dataset.file);
                        // 移除其他项的激活状态
                        fileList.querySelectorAll('a').forEach(a => a.classList.remove('active'));
                        // 添加当前项的激活状态
                        this.classList.add('active');
                    });
                });
            }
        })
        .catch(error => console.error('加载文件列表失败：', error));
}

// 加载文件内容
function loadFileContent(filename) {
    fetch(`/api/file/${filename}`)
        .then(response => response.json())
        .then(data => {
            const contentTable = document.getElementById('contentTable');
            if (contentTable && data.success) {
                const tbody = contentTable.querySelector('tbody');
                tbody.innerHTML = data.data.map((item, index) => `
                    <tr>
                        <td>${item.description}</td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="generateImage('${item.prompt.replace(/'/g, "\\'")}')">生成图片</button>
                        </td>
                    </tr>
                `).join('');
            } else if (!data.success) {
                alert(data.error || '加载文件内容失败');
            }
        })
        .catch(error => console.error('加载文件内容失败：', error));
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadFileList();
});