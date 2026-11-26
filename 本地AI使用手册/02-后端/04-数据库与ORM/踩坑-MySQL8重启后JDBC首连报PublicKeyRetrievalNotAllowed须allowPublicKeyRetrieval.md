# 踩坑：MySQL8 重启后 JDBC 首连报 Public Key Retrieval is not allowed，须 allowPublicKeyRetrieval=true

- 状态：`verified`（2026-11-18 本机 A/B 实测：不带参启动失败、带参启动成功并接口取数）
- 分类：02-后端/04-数据库与ORM
- 关联：`G:\AIrenwu\01_任务归档\2026-11-15_课程作业档案\01_报告\跨平台应用开发-档案.md` 第五节

## 触发

Spring Boot jar（内嵌 mysql-connector-java 8.0.23）连 MySQL 8（账号 caching_sha2_password），JDBC URL 带 `useSSL=false`；**mysqld 重启后的第一次连接**启动失败。服务一直活着时连接正常，故平时不暴露。

## 复现

本机便携 mysqld（`--port=3308 --datadir=C:\Users\Admin\foodserver-run\data`，root/123456）重启后，起课程后端：
`java -jar "E:\数据库服务启动\foodserver-0.0.1-SNAPSHOT.jar" "--spring.datasource.url=jdbc:mysql://127.0.0.1:3308/fooddb?serverTimezone=UTC&useUnicode=true&useSSL=false&characterEncoding=utf8"`
→ 进程退出，启动日志报连接异常。

## 证据

- 失败栈（jar 控制台原文）：`java.sql.SQLNonTransientConnectionException: Public Key Retrieval is not allowed`
- 同命令 URL 追加 `&allowPublicKeyRetrieval=true` 后：Tomcat started on port 8090；`POST http://localhost:8090/foodapp/comments/getCommentsByFoodIdByPage`（body `{"foodid":1,"pageIndex":0,"pageSize":3}`）返回 `data.content` 三条、`totalElements=39`。

## 根因

- 事实：Connector/J 8 对 caching_sha2_password 账号，在服务端密码缓存为空（重启后）且连接非 SSL 时，需向服务器请求 RSA 公钥来加密密码；连接器默认 `allowPublicKeyRetrieval=false`，拒绝取公钥 → 抛上述异常。
- 推断（机制层，未对照连接器源码逐行验证）：缓存命中或 SSL 通道下不需要取公钥，所以"服务不重启就没事"。

## 最小修复

JDBC URL 追加 `&allowPublicKeyRetrieval=true`。不改服务器账号插件、不开 SSL（改动面更大，且课程 jar 配置写死 useSSL=false 风格）。

## 验证命令与结果

见"证据"两条：不带参=启动失败（exit 1 + 上述栈）；带参=启动成功 + 接口 200 取数。2026-11-18 实测。

## 适用

MySQL 8 + caching_sha2_password + Connector/J 8.x + 非 SSL 连接；mysqld/服务器重启后首连最易触发。账号为 mysql_native_password 或走 SSL 时不触发。

## 剩余风险

`allowPublicKeyRetrieval=true` 官方提示存在中间人取公钥的风险面；本机 loopback 可接受，公网链路不要默认开。
