# Test1 项目

## 环境配置

本项目使用 conda 虚拟环境管理。

### 环境信息

- 环境名称: `test1`
- Python 版本: 3.11
- 包管理器: conda + pip

### 激活环境

#### 方法 1: 手动激活

```bash
conda activate test1
```

#### 方法 2: 自动激活 (推荐)

如果您的 shell 支持 direnv，进入项目目录时会自动激活环境。

安装 direnv:

```bash
# macOS
brew install direnv

# 在shell配置文件中添加 (zsh)
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
```

### 安装依赖

```bash
# 激活环境后
pip install -r requirements.txt
```

### 退出环境

```bash
conda deactivate
```

## 项目结构

```
test1/
├── .conda-project    # conda项目配置
├── .envrc           # direnv配置
├── .direnv          # direnv配置
├── README.md        # 项目说明
└── requirements.txt # Python依赖 (可选)
```
