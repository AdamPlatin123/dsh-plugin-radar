# 服务器迁移手册（docs/RUNBOOK.md）

> P8 生产切换操作手册：重构合入后把服务器侧（`~/dsh-external-research` + `~/dsh-k8s`）
> 切到新布局。冻结窗口与回滚见下。

## 前置

- [ ] 镜像仓 main 已合入全部 refactor-p* 批次，runner-smoke 全绿
- [ ] 快照同步正常 ≥ 一个完整日更周期（data-freshness 无告警）
- [ ] `.cron-state.json` / crontab 已备份（`crontab -l > ~/crontab.bak.$(date +%F)`）

## 冻结窗口（UTC 19:00–21：00，快照低峰）

1. 服务器 crontab 全量注释（probe / watchdog / discover / cadence 四条）
2. 等在途 bot PR 全部 MERGED（`gh pr list --repo dsh-external/awesome-dsh-plugins`）
3. 停 org→mirror 同步（auto-snapshot-push 不再被 probe 触发即停；≤2h 可接受）

## 切换步骤

```bash
cd ~/dsh-external-research
git pull dsh-ext main --ff-only          # 拿到含 engine/ 新布局的 main

# scripts/ 转发壳已随 main 提供（gen_plugins_all/export-data 等）；
# crontab 旧路径（scripts/cron-check.sh 等）由壳转发到 engine/，可暂不改 crontab。
# 建议逐条验证后再把 crontab 切到 engine/ 绝对路径：

bash engine/discovery/selftest… # 冒烟（按需）
python3 scripts/selftest-cron-increment.sh   # 增量检测四用例
bash scripts/selftest-merge-guard.sh         # 门控五用例（需 python3）

# 状态文件重建（修复后的增量检测从正确基线起步）：
#   .cron-state.json 按 .scope-current.txt + remote_head 重跑一轮 detect 即自愈

# 密钥迁移（P2b 契约）：
install -m 600 /dev/null ~/.radar-keys/deepseek
#   写入 DeepSeek key（或 export DEEPSEEK_API_KEY 于 crontab 头）

# dashboard 端口统一：
export RADAR_DASH_PORT=8898   # 或写入 ~/.dsh-radar.env
```

## 双轨观察（7 天）

- `legacy-compare-mainline.sh` 与 `compat/compare-mainline.sh` 并行 `--dry-run`，
  diff 两版 `[对比]` 输出应逐字节一致；观察期满删除 legacy。
- 每日对照冻结指标：plugins-all 条数、七档统计、PLUGINS-ALL 渲染幂等。
- enrich-metadata / site-build-deploy 首轮运行后检查 Pages 站点与 enrich sidecar。

## 回滚

- 代码：`git revert <refactor-pN 合并提交>` → 服务器 `git pull` + 恢复 crontab 备份。
- 站点：Actions 页面 Re-deploy 上一成功 artifact（秒级）。
- 数据面：canonical 为纯新增中间产物，旧消费链在观察期内完整保留——无回滚风险。

## 私有件边界

`~/dsh-k8s` 不动；全部引用点已加在场守卫（缺件 WARN 降级，见
`engine/ops/private/MANIFEST.md`）。新增私有件目录覆盖：
`export RADAR_K8S_DIR=…`（默认 `~/dsh-k8s`）。
