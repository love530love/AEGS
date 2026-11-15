# Doctor 与架构快照 Diff

## `aegs doctor`

`doctor` 是只读的接管前健康检查。它汇总：

- Charter、State 与事件账本验证；
- `takeover` 的 PASS/STALE/HOLD 结果；
- 当前架构快照是否存在。

它不是认证系统、恶意篡改检测或生产部署许可。任何 `STALE`/`HOLD` 都要求 Agent 保持只读，先刷新证据或请求人类方向。

## `aegs architecture diff`

两个架构快照之间可比较新增、删除、元数据变化的文件，以及新增/删除的静态推断关系：

```powershell
python -m aegs.cli architecture list .
python -m aegs.cli architecture diff . --from AS-<old> --to AS-<new>
```

当前实现以文件类别和字节数识别元数据变化，尚未比较内容哈希；关系来自静态导入推断，不是运行时证明。因此 Diff 是人工审查与实验设计的输入，而非自动批准依据。
