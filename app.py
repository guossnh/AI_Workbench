from flask import Flask, render_template, jsonify, request
from flask_bootstrap import Bootstrap
import pandas as pd
import os
import requests
import base64

# 禁用代理
os.environ['NO_PROXY'] = '*'

app = Flask(__name__)
Bootstrap(app)

# 火山引擎API配置
VOLCENGINE_API_HOST = 'https://open.volcengineapi.com'
VOLCENGINE_API_PATH = '/ImageGeneration/2023-08-01/cv'
VOLCENGINE_SERVICE = 'cv'
VOLCENGINE_REGION = 'cn-north-1'

# 从文件读取AccessKey信息
with open(os.path.join(os.path.dirname(__file__), 'AccessKey.txt'), 'r') as f:
    lines = f.readlines()
    ACCESS_KEY_ID = lines[0].split(': ')[1].strip()
    SECRET_ACCESS_KEY = lines[1].split(': ')[1].strip()

# 确保data目录存在
data_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manage')
def manage():
    return render_template('manage.html')

@app.route('/api/files')
def get_files():
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    return jsonify(files)

@app.route('/api/file/<filename>')
def get_file_content(filename):
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
        # 尝试不同的编码方式读取文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                # 确保数据至少有一列
                if len(df.columns) < 1:
                    return jsonify({
                        'success': False,
                        'error': 'CSV文件必须包含至少一列：场景描述'
                    })
                # 使用第一列数据作为场景描述和提示词
                data = [{
                    'description': row[0],
                    'prompt': row[0]
                } for _, row in df.iterrows()]
                return jsonify({
                    'success': True,
                    'data': data
                })
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，返回错误信息
        return jsonify({
            'success': False,
            'error': '无法识别文件编码格式，请确保文件使用UTF-8或GBK编码'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            })

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            })

        if not file.filename.endswith('.csv'):
            return jsonify({
                'success': False,
                'error': '只能上传CSV文件'
            })

        file_path = os.path.join(os.path.dirname(__file__), 'data', file.filename)
        file.save(file_path)

        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            })

        os.remove(file_path)
        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/generate-images', methods=['POST'])
def generate_images():
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': '缺少提示词参数'
            })

        # 清理之前生成的图片
        static_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
        if os.path.exists(static_dir):
            for file in os.listdir(static_dir):
                if file.endswith('.png'):
                    try:
                        os.remove(os.path.join(static_dir, file))
                    except Exception as e:
                        print(f'删除文件失败: {file}, 错误: {str(e)}')

        # 计算火山引擎API签名
        from datetime import datetime
        import hmac
        import hashlib
        import base64
        import json

        # 准备请求参数
        request_parameters = {
            "req_key": "high_aes_general_v21_L",
            "prompt": data['prompt'],
            "model_version": "general_v2.1_L",
            "req_schedule_conf": "general_v20_9B_pe",
            "llm_seed": -1,
            "seed": -1,
            "scale": 3.5,
            "ddim_steps": 25,
            "width": 512,
            "height": 512,
            "use_pre_llm": data.get('usePreLlm', True),
            "use_sr": True,
            "sr_seed": -1,
            "sr_strength": 0.4,
            "sr_scale": 3.5,
            "sr_steps": 20,
            "is_only_sr": False,
            "return_url": True,
            "logo_info": {
                "add_logo": True,
                "position": 0,
                "language": 0,
                "opacity": 0.3,
                "logo_text_content": "千草堂"
            }
        }
        request_body = json.dumps(request_parameters)

        # 准备查询参数
        query_params = {
            'Action': 'CVProcess',
            'Version': '2022-08-31',
        }
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(query_params.items())])

        # 准备请求时间
        current_date = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        datestamp = current_date[:8]

        # 计算内容哈希
        payload_hash = hashlib.sha256(request_body.encode('utf-8')).hexdigest()

        # 构造规范请求
        host = 'visual.volcengineapi.com'
        content_type = 'application/json'
        signed_headers = 'content-type;host;x-content-sha256;x-date'
        canonical_headers = f"content-type:{content_type}\nhost:{host}\nx-content-sha256:{payload_hash}\nx-date:{current_date}\n"
        canonical_request = f"POST\n/\n{query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        # 计算签名
        algorithm = 'HMAC-SHA256'
        credential_scope = f"{datestamp}/cn-north-1/cv/request"
        string_to_sign = f"{algorithm}\n{current_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        # 计算签名密钥
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        k_date = sign(SECRET_ACCESS_KEY.encode('utf-8'), datestamp)
        k_region = sign(k_date, 'cn-north-1')
        k_service = sign(k_region, 'cv')
        signing_key = sign(k_service, 'request')

        # 计算最终签名
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # 生成授权头
        authorization = f"{algorithm} Credential={ACCESS_KEY_ID}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        # 准备请求头
        headers = {
            'Content-Type': content_type,
            'X-Date': current_date,
            'Authorization': authorization,
            'X-Content-Sha256': payload_hash
        }

        # 发送请求
        response = requests.post(
            url=f"https://{host}/?{query_string}",
            headers=headers,
            data=request_body
        )

        if response.status_code != 200:
            error_message = '图片生成失败：'
            try:
                error_data = response.json()
                error_code = error_data.get('code', 0)
                
                # 根据错误码返回友好的错误提示
                error_messages = {
                    50411: '输入图片未通过安全审核',
                    50511: '生成的图片未通过安全审核',
                    50412: '输入文本未通过安全审核',
                    50512: '生成的文本未通过安全审核',
                    50413: '输入文本包含敏感内容或受限信息'
                }
                
                if error_code in error_messages:
                    error_message += error_messages[error_code]
                else:
                    if 'message' in error_data:
                        error_message += error_data['message']
                    elif 'error' in error_data:
                        error_message += error_data['error']
                    else:
                        error_message += f'未知错误（状态码：{response.status_code}）'
            except:
                error_message += f'服务响应异常（状态码：{response.status_code}）'
            
            return jsonify({
                'success': False,
                'error': error_message
            })

        # 将生成的图片保存到静态文件夹
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        images = []
        response_data = response.json()
        
        # 处理API返回的图片数据
        if 'data' in response_data and 'image_urls' in response_data['data'] and len(response_data['data']['image_urls']) > 0:
            for i, image_url in enumerate(response_data['data']['image_urls']):
                # 下载图片
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    image_path = f"/static/images/{data['prompt']}_{i}.png"
                    with open(os.path.join(os.path.dirname(__file__), image_path.lstrip('/')), 'wb') as f:
                        f.write(image_response.content)
                    images.append(image_path)
                else:
                    print(f'下载图片失败: {image_url}, 状态码: {image_response.status_code}')
        else:
            return jsonify({
                'success': False,
                'error': '生成图片失败：API返回数据格式不正确'
            })

        return jsonify({
            'success': True,
            'images': images
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)