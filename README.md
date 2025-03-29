# WeChat AI 助手

这是一个基于微信公众号的AI助手项目，使用Python开发，支持与用户进行智能对话。

## 功能特点

- 支持微信公众号消息接收和回复
- 集成DeepSeek AI模型进行智能对话
- 支持长消息自动分段发送
- 支持专业领域（如网络安全）的专业回答
- 支持自由对话模式
- 完善的错误处理和日志记录

## 系统数学架构

本系统的数学架构可以从以下几个维度描述：

### 1. 消息处理映射函数

系统处理消息的流程可表示为映射函数 $f: M \rightarrow R$，其中：
- $M$ 表示消息空间，包含用户发送的各类消息 $m \in M$
- $R$ 表示响应空间，包含系统可能的响应 $r \in R$

对于文本消息处理：
$$f_\text{text}(m) = g(h(m, c))$$

其中：
- $h: M \times C \rightarrow Q$ 是上下文合并函数，将消息 $m$ 与会话上下文 $c \in C$ 合并
- $g: Q \rightarrow R$ 是AI推理函数，将查询 $q \in Q$ 映射到响应 $r$

消息空间可进一步分解为：
$$M = M_\text{text} \cup M_\text{voice} \cup M_\text{event}$$

每种消息类型映射到不同的处理函数：
$$
\begin{cases}
f_\text{text}: M_\text{text} \rightarrow R_\text{text} \\
f_\text{voice}: M_\text{voice} \rightarrow R_\text{text} \\
f_\text{event}: M_\text{event} \rightarrow R_\text{event}
\end{cases}
$$

### 2. 会话状态转换

会话状态可以表示为有限状态机：
$$S_{t+1} = \delta(S_t, m_t)$$

其中：
- $S_t$ 是时间 $t$ 的会话状态，包含历史消息序列
- $m_t$ 是时间 $t$ 的用户输入
- $\delta$ 是状态转换函数

会话状态 $S_t$ 可以表示为消息序列：
$$S_t = \{m_0, r_0, m_1, r_1, ..., m_{t-1}, r_{t-1}\}$$

其中 $m_i$ 是用户消息，$r_i$ 是系统响应。

会话修剪算法可以表示为：
$$S'_t = \phi(S_t, \tau)$$

其中：
- $\phi$ 是修剪函数
- $\tau$ 是token数量阈值（本系统中为 $\tau = 1000$）
- $S'_t$ 是修剪后的会话状态

具体的修剪函数实现为：
$$\phi(S_t, \tau) = 
\begin{cases}
S_t, & \text{如果} \sum_{i=0}^{t-1} (|m_i| + |r_i|) \cdot \alpha \leq \tau \\
\{m_0, r_0\} \cup \{m_{t-k}, r_{t-k}, ..., m_{t-1}, r_{t-1}\}, & \text{否则}
\end{cases}$$

其中：
- $|m_i|$ 和 $|r_i|$ 是消息的字符长度
- $\alpha$ 是字符到token的转换系数（约0.7）
- $k$ 是保留的最近消息数量，使得 $\sum_{i=t-k}^{t-1} (|m_i| + |r_i|) \cdot \alpha \leq \tau$

### 3. AI响应生成

AI响应生成过程可以表示为条件概率最大化问题：
$$r^* = \arg\max_{r \in R} P(r|q, \theta)$$

其中：
- $q$ 是包含上下文的查询
- $\theta$ 是模型参数（DeepSeek-R1模型）
- $r^*$ 是最优响应

在DeepSeek模型中，条件概率通过自回归方式计算：
$$P(r|q,\theta) = \prod_{i=1}^{n} P(r_i|q,r_1,...,r_{i-1},\theta)$$

其中，$r_i$ 是响应中的第 $i$ 个token。

在实际计算中，使用以下参数影响生成：
- 温度系数 $T = 0.7$，控制随机性
- 采样概率阈值 $p_{top} = 0.95$，过滤低概率token
- 最大生成token数 $n_{max} = 2000$

预测过程可描述为：
$$r_i \sim \text{softmax}\left(\frac{f_\theta(q,r_1,...,r_{i-1})}{T}\right)$$

其中 $f_\theta$ 是神经网络输出的logits。

### 4. 请求超时计算

系统使用动态超时计算函数：
$$T(m) = T_\text{base} + \min(30, \lfloor \frac{\max(0, |m| - 200)}{100} \rfloor \cdot 5)$$

其中：
- $T_\text{base}$ 是基础超时时间（默认60秒）
- $|m|$ 是消息长度

这可进一步表示为分段函数：
$$T(m) = 
\begin{cases}
T_\text{base}, & \text{如果 } |m| \leq 200 \\
T_\text{base} + \min(30, \lfloor \frac{|m| - 200}{100} \rfloor \cdot 5), & \text{如果 } |m| > 200
\end{cases}$$

在系统实现中，超时与响应质量的关系可表示为：
$$Q(r) \propto \min(Q_{max}, \log(T(m)))$$

其中 $Q(r)$ 表示响应质量，$Q_{max}$ 是质量上限。

### 5. 重试机制

系统使用指数退避策略进行重试：
$$t_\text{wait}(n) = 2n$$

其中：
- $n$ 是当前重试次数
- $t_\text{wait}$ 是等待时间（秒）

重试概率空间建模：
设 $P_s(n)$ 是第 $n$ 次尝试成功的概率，则总成功概率为：
$$P_{总} = 1 - \prod_{i=0}^{N_{max}}(1 - P_s(i))$$

其中 $N_{max}$ 是最大重试次数（系统中为2）。

假设每次尝试的成功概率为常数 $p$，则：
$$P_{总} = 1 - (1-p)^{N_{max}+1}$$

### 6. 消息分段算法

长消息自动分段算法可以表述为分片函数 $\Psi: R \rightarrow R^k$：
$$\Psi(r) = (r^{(1)}, r^{(2)}, ..., r^{(k)})$$

其中：
- $r$ 是原始响应
- $r^{(i)}$ 是第 $i$ 个分段
- $k$ 是分段数量

分段过程满足：
1. 长度约束：$\forall i, |r^{(i)}| \leq L_{max}$，其中 $L_{max}$ 是单条消息最大长度（2000字）
2. 完整性约束：$r = r^{(1)} \oplus r^{(2)} \oplus ... \oplus r^{(k)}$，其中 $\oplus$ 是字符串连接操作
3. 边界约束：分段应在自然断句处，对于分段点 $b_i$，优先选择 $r[b_i] \in \{。, ！, ？, ., !, ?\}$

### 7. 并发请求处理模型

并发处理可以用生产者-消费者模型描述：
$$Q_t = Q_{t-1} \cup P_t - C_t$$

其中：
- $Q_t$ 是时间 $t$ 的请求队列
- $P_t$ 是时间 $t$ 的新增请求集
- $C_t$ 是时间 $t$ 处理完成的请求集

系统线程模型可表示为：
$$T = \{T_{main}, T_{http}, T_{worker_1}, ..., T_{worker_n}\}$$

其中各线程之间的同步使用互斥锁 $\mu$ 和条件变量 $cv$ 实现：
$$\begin{align}
acquire(\mu) &: \text{获取锁} \\
release(\mu) &: \text{释放锁} \\
wait(cv, \mu) &: \text{等待条件变量，同时释放锁} \\
notify(cv) &: \text{唤醒等待该条件的一个线程}
\end{align}$$

### 8. 矩阵变换与嵌入表示

在DeepSeek模型中，消息序列首先转换为token序列，然后嵌入为高维向量：
$$\mathbf{E} = \text{Embedding}(\text{Tokenize}(m)) \in \mathbb{R}^{L \times d}$$

其中：
- $L$ 是序列长度
- $d$ 是嵌入维度（通常为4096）

自注意力机制计算公式：
$$\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}\right)\mathbf{V}$$

其中 $\mathbf{Q}, \mathbf{K}, \mathbf{V} \in \mathbb{R}^{L \times d}$ 是查询、键、值矩阵。

多头注意力机制：
$$\text{MultiHead}(\mathbf{X}) = \text{Concat}(\text{head}_1, ..., \text{head}_h)\mathbf{W}^O$$

其中：
$$\text{head}_i = \text{Attention}(\mathbf{X}\mathbf{W}_i^Q, \mathbf{X}\mathbf{W}_i^K, \mathbf{X}\mathbf{W}_i^V)$$

### 9. 系统性能与资源分析

系统性能可以用响应时间分布建模：
$$T_{resp} = T_{queue} + T_{process} + T_{api} + T_{send}$$

其中各部分的统计特性可以用概率分布表示：
- $T_{queue} \sim \text{Exp}(\lambda_q)$：队列等待时间服从指数分布
- $T_{process} \sim \mathcal{N}(\mu_p, \sigma_p^2)$：处理时间服从正态分布
- $T_{api} \sim \text{LogNormal}(\mu_a, \sigma_a^2)$：API调用时间服从对数正态分布
- $T_{send} \sim \text{Exp}(\lambda_s)$：发送时间服从指数分布

系统资源使用模型：
$$\begin{align}
\text{CPU}_t &= \alpha_c \cdot N_{req/s} + \beta_c \\
\text{MEM}_t &= \alpha_m \cdot N_{active} + \beta_m
\end{align}$$

其中：
- $N_{req/s}$ 是每秒请求数
- $N_{active}$ 是活跃会话数
- $\alpha_c, \beta_c, \alpha_m, \beta_m$ 是系统特定常数

## 开发环境与技术栈

本项目基于以下技术栈开发：

- **编程语言**: Python 3.8+
- **web框架**: 原生HTTP服务器（http.server）
- **AI模型**: DeepSeek-R1（通过API调用）
- **图像处理**: Pillow库
- **系统集成**: Windows/Linux系统API
- **打包工具**: PyInstaller

## 系统要求

- Python 3.8+
- Windows 10/11 或 Linux 系统（CentOS 7+/Ubuntu 18.04+）
- 微信公众号开发者账号
- 公网IP或域名（用于微信服务器回调）
- 最小配置：1核CPU，1GB内存，10GB存储空间

## 安装步骤

1. 克隆项目到本地：
```bash
git clone [项目地址]
cd wehcat
```

2. 安装依赖包：
```bash
pip install -r requirements.txt
```

3. 配置微信公众号：
   - 登录微信公众平台
   - 获取AppID和AppSecret
   - 配置服务器地址和Token
   - 配置消息加解密密钥

4. 修改配置文件：
   - 打开 `config.json`
   - 填入您的微信公众号配置信息
   - 配置AI模型参数

## 微信公众号配置详解

### 1. 申请微信公众号

1. 访问[微信公众平台](https://mp.weixin.qq.com/)注册账号
2. 选择"服务号"类型（推荐，功能更完整）
3. 完成企业资质认证（个人可选择订阅号）

### 2. 配置服务器

1. 登录微信公众平台，进入"设置与开发" → "基本配置"
2. 在"服务器配置"部分，填写以下信息：
   - **服务器地址(URL)**: `http://您的域名或IP/wechat`（必须是公网可访问的地址）
   - **令牌(Token)**: 自定义字符串，与config.json中的`wechat_mp_token`保持一致
   - **消息加解密密钥(EncodingAESKey)**: 点击"随机生成"，并复制到config.json中的`wechat_mp_aes_key`
   - **消息加解密方式**: 选择"安全模式"（推荐）

3. 记录微信公众号的AppID和AppSecret，填入config.json中对应字段

### 3. 配置IP白名单

1. 在"设置与开发" → "基本配置" → "IP白名单"中
2. 添加您服务器的公网IP地址
3. 如有多台服务器，全部添加

### 4. 配置消息与菜单

1. 进入"设置与开发" → "功能设置"
2. 启用"自动回复"功能
3. 可选：配置自定义菜单，增加用户交互功能

## 服务器部署指南

### Linux服务器部署

#### 环境准备（CentOS 7）

```bash
# 安装Python和依赖
yum update -y
yum install -y python38 python38-devel python38-pip gcc make
yum install -y epel-release
yum install -y python-pillow
pip3 install --upgrade pip

# 安装项目依赖
cd /path/to/wehcat
pip3 install -r requirements.txt
```

#### 环境准备（Ubuntu 18.04/20.04）

```bash
# 安装Python和依赖
apt update
apt install -y python3.8 python3.8-dev python3-pip python3-venv
apt install -y build-essential libssl-dev libffi-dev

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装项目依赖
cd /path/to/wehcat
pip install -r requirements.txt
```

#### 使用systemd管理服务

1. 创建服务文件：

```bash
sudo nano /etc/systemd/system/wechat-ai.service
```

2. 添加以下内容：

```
[Unit]
Description=WeChat AI Assistant Service
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/wehcat
ExecStart=/usr/bin/python3 app.py
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=wechat-ai

[Install]
WantedBy=multi-user.target
```

3. 启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable wechat-ai
sudo systemctl start wechat-ai
sudo systemctl status wechat-ai
```

#### 使用Nginx反向代理（可选）

1. 安装Nginx：

```bash
# CentOS
yum install -y nginx

# Ubuntu
apt install -y nginx
```

2. 配置Nginx：

```bash
sudo nano /etc/nginx/conf.d/wechat-ai.conf
```

3. 添加配置：

```
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

4. 重启Nginx：

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### Windows服务器部署

#### 环境准备

1. 下载并安装[Python 3.8+](https://www.python.org/downloads/windows/)
2. 安装依赖：

```cmd
cd C:\path\to\wehcat
pip install -r requirements.txt
```

#### 配置防火墙

1. 打开Windows Defender防火墙
2. 添加入站规则，允许80端口（或您配置的其他端口）

#### 注册为Windows服务

1. 安装NSSM（Non-Sucking Service Manager）：
   - 下载[NSSM](https://nssm.cc/download)
   - 解压到任意目录

2. 使用NSSM创建服务：

```cmd
nssm.exe install WeChatAI
```

3. 在弹出的配置窗口中：
   - **Path**: 选择Python安装路径（如`C:\Python38\python.exe`）
   - **Startup directory**: 项目目录（如`C:\path\to\wehcat`）
   - **Arguments**: `app.py`
   - **详细设置**: 设置服务自动启动、失败时自动重启等

4. 管理服务：

```cmd
nssm.exe start WeChatAI
nssm.exe status WeChatAI
```

## 编译打包教程

### 编译准备

1. 安装PyInstaller：

```bash
pip install pyinstaller
```

2. 确保所有依赖已安装：

```bash
pip install -r requirements.txt
```

### Windows系统编译

1. 基本编译：

```cmd
pyinstaller --clean --onefile app.py
```

2. 使用规范文件（推荐）：

```cmd
pyinstaller --clean wechat.spec
```

3. 自定义图标编译：

```cmd
pyinstaller --icon=app_icon.ico --clean --onefile app.py
```

### Linux系统编译

1. 基本编译：

```bash
pyinstaller --clean --onefile app.py
```

2. 使用规范文件：

```bash
pyinstaller --clean wechat.spec
```

### 自定义图标说明

项目支持自定义Windows任务栏和系统托盘图标：

1. 准备图标文件：
   - 准备一个.ico格式的图标文件（推荐尺寸：256x256）
   - 将图标文件命名为`app_icon.ico`并放在项目根目录

2. 转换图标（如果有非.ico格式图像）：

```bash
python convert_icon.py your_image.png
```

3. 修改图标代码（可选）：
   - 编辑`app_icons.py`文件
   - 修改`ICON_BASE64`变量为新图标的Base64编码

4. 在spec文件中指定图标：
   - 编辑`wechat.spec`文件
   - 找到`exe = EXE(...)`部分
   - 确保`icon='app_icon.ico'`正确设置

## 使用方法

### 基本使用

1. 启动服务：

```bash
# Linux
python3 app.py

# Windows
python app.py
```

2. 服务成功启动后，会在命令行显示：
   ```
   ======== 微信AI助手服务启动 ========
   服务地址: 0.0.0.0:80
   认证方式: compatible
   API基础URL: https://your-api-url.com
   使用模型: deepseek-r1
   ====================================
   ```

3. 在微信公众号发送消息，机器人会自动回复

### 管理命令

- 查看服务状态：
  ```bash
  # Linux
  systemctl status wechat-ai
  
  # Windows
  nssm status WeChatAI
  ```

- 重启服务：
  ```bash
  # Linux
  systemctl restart wechat-ai
  
  # Windows
  nssm restart WeChatAI
  ```

### 用户交互

1. 关注配置好的微信公众号
2. 向公众号发送文本消息
3. 系统会调用DeepSeek AI模型处理请求并返回回复
4. 如果回复较长，系统会自动分段发送

## 配置说明

主要配置项（config.json）：

```json
{
  "model": "deepseek-r1",
  "open_ai_api_key": "您的API密钥",
  "open_ai_api_base": "API基础地址",
  "wechat_mp_token": "微信公众号Token",
  "wechat_mp_app_id": "微信公众号AppID",
  "wechat_mp_app_secret": "微信公众号AppSecret",
  "wechat_mp_aes_key": "消息加解密密钥",
  "wechat_mp_port": 80,
  "wechat_mp_address": "0.0.0.0"
}
```

## 常见问题

1. 端口被占用
   - 检查80端口是否被其他程序占用
   - 可以在配置文件中修改端口号

2. 消息发送失败
   - 检查网络连接
   - 确认API密钥是否有效
   - 查看日志文件排查具体原因

3. 程序无法启动
   - 检查Python环境是否正确安装
   - 确认所有依赖包已安装
   - 查看错误日志定位问题

4. 微信公众号未收到回复
   - 确认服务器URL配置是否正确
   - 检查服务器防火墙是否开放相应端口
   - 验证Token配置是否一致

5. 回复速度慢
   - 检查网络连接质量
   - 考虑调整API超时设置
   - 可能是AI模型处理时间较长，属于正常现象

## 日志说明

- 日志文件位于 `logs` 目录下
- 按日期自动分割日志文件
- 可通过配置文件调整日志级别

## 更新说明

### v1.0.0
- 初始版本发布
- 支持基本的消息收发功能
- 集成DeepSeek AI模型
- 支持长消息自动分段

## 联系方式

如有问题或建议，请提交Issue或联系管理员。

## 许可证

本项目采用 MIT 许可证 