---
title: "对陌生 API 做批量探测时，按 URL 子串判「读/写」会误伤：register 里含 get，一个 POST {} 就往用户库里插了一行"
date: 2026-11-04
domain: common
category: 调试与验证
status: verified
severity: high
stack: [Spring Boot, Swagger2, MySQL, Python urllib]
tags: [API探测, 只读保证, 副作用, swagger, 误判读写, 自我损害披露]
---

# 问题：想"只读探测"一个后端，结果自己造了一次写库

## 一句话结论

**判端点读写只能看它自己的声明（`@RequestMapping` 方法 + 语义），不能看 URL 里有没有 `list/get/find` 这类子串**；
我用关键字白名单把 `/user/register` 归进了"读端点"（因为 `register` 里含 `get`），
对它发了 `POST {}`，Spring 照单全收并插入了一行全 NULL 的用户记录。
"我不会改你数据"这句承诺，需要一个**具体的、按语义筛过的**执行方案来兜，而不是靠一个启发式集合。

## 触发条件与影响

- 环境：Spring Boot 2.4.3 + Swagger2 + MySQL 8（`fooddb`），jar 在 `H:\下载`，端口 8090，context-path `/foodapp`
- 触发条件：批量探测 16 个端点，用 `READ_HINTS=("list","findone","get","select",...)` 与
  `WRITE_HINTS=("add","save","update","delete",...)` 两个子串集合分类
- 具体误判：`register` ⊃ `get` ⇒ 进了读集合；`WRITE_HINTS` 里**没有** `register/login/upload`
- 影响：`t_users` 多出 `id=77`、其余字段全 NULL 的一行（表内原本 5 行）

## 复现步骤

1. 前置：`/v2/api-docs` 可读，拿到 16 条路径与参数
2. 操作：对分类为"读"的端点逐个 `POST {}`（Content-Type: application/json）
3. 预期：只读端点返回数据，不产生副作用
4. 实际：`/user/register` 返回 `{"msg":"成功","data":{"id":77,"username":null,...},"success":true}` ⇒ **写库成功**

## 证据

- 探测输出：`[读通] POST /user/register -> 200 '{"msg":"成功","data":{"id":77,...,"password":null},"success":true}'`
- 事后查库（只读）：`select ... from fooddb.t_users where id>=76` ⇒ 一行 `77 NULL NULL NULL NULL NULL`，`count(*)=5`
- 同一批里被我的启发式**正确**跳过的写端点只有 2 个（`/comments/add`、`/user/upload_headpic`），
  说明漏判面很大：`login/register` 这类"动作型"端点完全不在关键字表里

## 根因分析

- 已确认根因：用 URL 子串做读写分类，等于用**命名习惯**代替**接口语义**；
  而这个项目的端点全部是 POST（连 `list/findone` 都是），"POST ⇒ 可能是写"这条最朴素的防线也被我的分类器绕过了。
- 排除过的假设：①"Spring 会因必填 body 参数而拒绝空对象"—— 不会，`@RequestBody Users` 收到 `{}` 就是全 null 实体，
  `save()` 照样成功；②"register 有唯一约束会挡住空行"—— 该表字段可空，没挡住。
- 问题归属：**本次修改引入**（我的探测脚本），不是应用故障

## 最小修复

**流程层面**（下次照做）：

1. 探测前先按**声明**筛：从 api-docs 取 `parameters[].required` 与 `in`，
   只打"无必填 body 参数"的端点；有必填 body 的一律跳过（空 body 只会得到 500 或全默认值写入）。
2. 把"动作型"动词显式列入黑名单：`register/login/logout/upload/download/pay/send/reset/submit/import/exec`，
   而不是只列 `add/update/delete`。
3. 更稳的做法：**先只打 `list` 类，确认服务活着就够**；要验证写路径时，用**事务回滚**或**测试库**，
   不在用户的生产/学习库上试。
4. 探测脚本收尾要**自证清白**：结束时对可能被动过的表做一次行数/最大 id 复核，并把结果打出来。

**本次数据修复**（等用户点头，因为是对他数据库的 DELETE）：

```sql
-- 内容已留档：id=77，其余 5 个字段全 NULL，删前表内 5 行
DELETE FROM fooddb.t_users WHERE id = 77 AND username IS NULL AND password IS NULL;
-- 期望 affected rows = 1
```

## 验证记录

- [x] 应用启动修复本身已验证：11/14 端点返回真实数据（`category/types/news/food/comments list` 都有内容）
- [x] 三个非 200 是**我发空 body** 造成的（`comments/findone`、`getCommentsByFoodIdByPage`、`user/login` 500），不是应用 bug
- [x] `*/findone` 返回 `NonUniqueResultException: query did not return a unique result: N` 同样是空 body ⇒ 匹配全表，
  属应用自身的脆弱点（没做空值校验），可反馈但不算我这次要修的
- [x] 误写行已取证留档（id、字段值、表行数），删除动作待确认
- [x] 无常驻进程：两次探测都 `terminate()` 掉 java，复核 8090 无监听

## 可复用规则

**给陌生后端做批量探测时，"只读"必须由接口的声明与参数形状来保证，不能由 URL 关键字来保证。**
具体闸门：①只打无必填 body 的端点；②动作型动词进黑名单；③结束时复核行数/最大 id 自证。
单次经验不外推：这条只适用于"对他人/用户数据所在实例做探测"，对自己新建的空测试库不适用。

## 适用范围与不适用范围

- 适用：任何对**已有数据**的接口做冒烟/审计/取证；Swagger/OpenAPI 批量调用
- 不适用：只读文档拉取、对新初始化测试库的功能验证
- 附带：本项目 16 个端点全是 POST，所以"用 GET 才安全"这种直觉在这里完全失效

## 剩余风险

- `t_users` 里那行 id=77 仍在（等用户确认删除）；auto-increment 已推进到 78，删行不会回退计数器（无实际影响）。2026-11-13 复核：MySQL80 服务在跑（3306），但本机 PATH 无 mysql 客户端、foodapp jar 已从 H 盘删除、手册不存凭据 ⇒ 无法代为执行上面带护栏的 DELETE；需用户自行执行或提供凭据。
- 该 jar 的 `findone` 系列对空 body 不设防，前端漏传参数会得到 500 或"非唯一结果"，是课程包自身的问题。

## 关联

- 相关记录：[[踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]（同为"我的探测/操作本身造出损害"）、
  [[规则-列表项累加先判派生视图再清源头数据]]
- 相关分类：03-通用/03-调试与验证
- 本机产物：`03_工具脚本\probe_foodserver_readonly.py`（含这次误判的分类器）、`%TEMP%\foodserver_probe2.log`
