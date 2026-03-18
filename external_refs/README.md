# external_refs

本目录用于存放只读参考代码，不属于主项目正式源码。

规则：
1. 仅供阅读、对照、让 Codex/VS Code 检索参考实现。
2. 不在此目录内做正式开发。
3. 不提交到主仓库。
4. 如需更新参考版本，可直接删除后重新 clone。

当前参考：
- rknn_model_zoo
  来源：https://github.com/airockchip/rknn_model_zoo
  用途：参考 RetinaFace 的 RKNNLite 推理入口、预处理、后处理、NMS、示例目录组织。