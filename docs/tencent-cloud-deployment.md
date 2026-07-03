# 腾讯云 Ubuntu + Docker 部署指南

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

```bash
cd GZ_hiddengems
git pull
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

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

当前 Nginx 配置默认只开放 HTTP，并且 `docker-compose.prod.yml` 只映射 `80:80`。生产推荐绑定域名后配置 HTTPS：

1. 将域名解析到腾讯云服务器公网 IP。
2. 申请证书。
3. 将证书放到 `backend/certs/`。
4. 修改 `deploy/nginx/default.conf`，增加 `listen 443 ssl;` 和证书路径。
5. 在 `backend/docker-compose.prod.yml` 的 `nginx.ports` 下增加 `443:443`。
6. 重启 Nginx：

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
