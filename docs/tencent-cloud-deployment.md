# 腾讯云 Ubuntu + Docker 部署指南

> 维护约定：以后处理本项目的首次部署、更新部署、启停服务和部署故障时，应先查阅本文件，并以当前仓库中的 `backend/docker-compose.prod.yml` 和 `deploy/nginx/default.conf` 为最终依据。

## 服务器准备

腾讯云安全组至少放行：

- `22`：SSH
- `80`：HTTP
- `443`：HTTPS，后续配置证书时再放行

服务器建议配置：

- Ubuntu 22.04 或 24.04
- Docker
- Docker Compose 插件
- 2C2G 起步，生产建议 2C4G 或更高

## 首次部署

登录服务器：

```bash
ssh ubuntu@你的服务器公网 IP
```

安装基础工具：

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
```

安装 Docker。如果服务器镜像已经带 Docker，可跳过：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

重新登录 SSH，让 Docker 用户组生效。

拉取代码：

```bash
git clone https://github.com/cms7058/GZ_hiddengems.git
cd GZ_hiddengems/backend
```

创建生产环境变量：

```bash
cp .env.prod.example .env
nano .env
```

必须修改：

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `DATABASE_URL` 中的 MySQL 密码，需与 `MYSQL_PASSWORD` 一致
- `JWT_SECRET_KEY`
- `INITIAL_ADMIN_PASSWORD`
- `MAP_API_KEY`

小程序公共数据服务的时间限制通过后台管理页面配置：进入“接口管理”中的“小程序数据时间管理”，设置启用开关与北京时间的开始、结束小时。启用后，小程序启动时先读取这项配置；超出开放时间时不加载后台数据并弹出提示。

该限制只作用于 `/api/v1` 下的小程序公共数据和提交接口，管理后台 `/admin`、后台管理接口 `/api/v1/admin`、小程序时间配置接口及 `/health` 健康检查保持全天可用。管理员保存新时间后立即生效，无需重启容器。

国内服务器构建镜像时默认使用腾讯云 Debian / PyPI 镜像源。如遇到包源不可用，可在 `.env` 中改成其他镜像：

```env
DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian
DEBIAN_SECURITY_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian-security
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
```

启动服务：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

查看服务：

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
```

访问：

```text
http://你的服务器公网 IP/admin
```

默认管理员由 `.env` 控制：

- `INITIAL_ADMIN_USERNAME`
- `INITIAL_ADMIN_PASSWORD`

首次登录后，后续应增加“修改管理员密码”功能或直接在数据库中更新密码。

## 更新部署

生产服务器目录为 `~/GZ_hiddengems`。推荐先备份数据库，再停止旧容器、拉取代码并重新构建。`docker compose down` 只删除容器和项目网络，不会删除 MySQL、Redis 或上传文件的数据卷。

可选：更新前备份数据库：

```bash
cd ~/GZ_hiddengems/backend
mkdir -p ~/gz-hidden-gems-backups
BACKUP_FILE=~/gz-hidden-gems-backups/gz_hidden_gems_$(date +%Y%m%d_%H%M%S).sql
docker compose -f docker-compose.prod.yml exec -T mysql sh -lc 'exec mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > "$BACKUP_FILE"
echo "$BACKUP_FILE"
```

标准更新流程：

```bash
cd ~/GZ_hiddengems/backend
docker compose -f docker-compose.prod.yml down

cd ~/GZ_hiddengems
git pull --ff-only origin main

cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

检查容器和 API 日志：

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 api
docker compose -f docker-compose.prod.yml logs --tail=100 nginx
```

验证 HTTPS、管理后台和 API：

```bash
curl -I https://hiddengems.pebs.tech/admin
curl --compressed 'https://hiddengems.pebs.tech/api/v1/tags?lang=zh-CN'
```

`curl -I /admin` 可能返回 `405 Method Not Allowed`，因为 `-I` 发出的是 `HEAD` 请求；这通常仍表示 HTTPS 和 Nginx 已连通。需要验证页面内容时使用：

```bash
curl --compressed https://hiddengems.pebs.tech/admin
```

API 启动时会通过 SQLAlchemy 创建缺失的数据表。本次新增的 `spot_child_points` 表会在启动时自动创建；不要为此删除或重建 MySQL 数据卷。

### 仅停止服务

需要暂时释放服务器内存和 CPU 时执行：

```bash
cd ~/GZ_hiddengems/backend
docker compose -f docker-compose.prod.yml down
```

重新启动现有镜像：

```bash
cd ~/GZ_hiddengems/backend
docker compose -f docker-compose.prod.yml up -d
```

严禁在保留生产数据的情况下执行以下命令：

```bash
docker compose -f docker-compose.prod.yml down -v
```

其中 `-v` 会删除 Compose 管理的 MySQL、Redis 和上传文件数据卷。

## 数据与文件

生产 Compose 使用 Docker volume 保存：

- `mysql_data`：MySQL 数据
- `redis_data`：Redis 数据
- `uploads_data`：后台上传的秘境图片

不要执行会删除 volume 的命令，除非确认要清空数据。

## 备份 MySQL

```bash
docker compose -f docker-compose.prod.yml exec mysql \
  mysqldump -u root -p gz_hidden_gems > gz_hidden_gems_backup.sql
```

恢复前请先停止业务访问，并确认数据库版本和备份文件。

## HTTPS

当前生产配置已启用 HTTPS：

- 域名：`hiddengems.pebs.tech`
- HTTP `80` 自动跳转到 HTTPS `443`
- Compose 已映射 `80:80` 和 `443:443`
- 证书目录：`backend/certs/`
- 证书文件：`hiddengems.pebs.tech.pem`
- 私钥文件：`hiddengems.pebs.tech.key`

服务器上的私钥权限应设置为仅所有者可读写：

```bash
chmod 600 ~/GZ_hiddengems/backend/certs/hiddengems.pebs.tech.key
```

更新证书后重启 Nginx：

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

## 常用排错

如果构建时报：

```text
Could not find a version that satisfies the requirement fastapi==0.111.0
```

通常是容器内无法访问默认 PyPI。先拉取最新代码，然后重新构建：

```bash
cd ~/GZ_hiddengems
git pull
cd backend
docker compose -f docker-compose.prod.yml build --no-cache api
docker compose -f docker-compose.prod.yml up -d
```

查看 API 日志：

```bash
docker compose -f docker-compose.prod.yml logs -f api
```

查看 Nginx 日志：

```bash
docker compose -f docker-compose.prod.yml logs -f nginx
```

进入 MySQL：

```bash
docker compose -f docker-compose.prod.yml exec mysql mysql -u root -p
```

重启全部服务：

```bash
docker compose -f docker-compose.prod.yml restart
```
