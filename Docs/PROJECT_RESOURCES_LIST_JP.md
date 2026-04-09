# プロジェクト・リソース・リスト (Scripts & Data)

本プロジェクト「PKGF Nature Analysis」に含まれるすべての実行スクリプト、数学コア、およびデータファイルのリストです。

## 1. 実行スクリプト & 数学コア (Scripts/)
プロジェクトの核心となる論理処理を行うスクリプト群です。個別の機能は `pkgf_master_pipeline.py` に統合されています。

| ファイル名 | 役割・機能 |
| :--- | :--- |
| `pkgf_master_pipeline.py` | **メイン・パイプライン**。21個のデータセットの一括解析、モデル化、可視化（similarity_map.png等）を統合的に実行する。 |
| `pkgf_math_core.f90` | **Fortran数学コア**。Hurst指数、フラクタル次元、Fisher情報量等の計算負荷の高いアルゴリズムを高速に処理する。 |
| `cross_validate_fortran.py` | **整合性検証スクリプト**。Python実装とFortran実装の計算結果を比較し、数学的正確性を保証する。 |

## 2. 観測生データ (Data/*_raw.csv)
自然界から収集された、解析の元となる **21個** のオリジナルの時系列データです。これに比較基準データ（Synthetic Ref.）を加えた **計22個のプロファイル** を解析対象としています。

*   `nile_raw.csv`, `sunspot_raw.csv`, `bitcoin_raw.csv`, `seismic_raw.csv` など。
*   （詳細は `Docs/DATASET_LIST_JP.md` を参照）

## 3. 解析済み幾何学的プロファイル (Data/*_morphic_profile.json)
`pkgf_master_pipeline.py` によって抽出された、データの幾何学的特徴を記録した JSON ファイルです。

*   Hurst指数、フラクタル次元、TDA、RQA、Fisher情報量など 30次元の特徴量が格納されています。

## 4. 合成モデルデータ (Data/synthetic_*_raw.csv)
論理プリミティブ（数式）から再生成された、オリジナルと「数学的に同じプロファイル」を持つデータです。

*   `synthetic_nile_raw.csv` など。これらは「見た目は違うが、中身（幾何学的構造）は同じ」複製体です。

## 5. 出力レポート・画像 (Docs/ & Data/)
プロジェクトの成果を可視化したファイルです。

| ファイル名 | 内容 |
| :--- | :--- |
| `Docs/similarity_map.png` | 全データセットの幾何学的類似性マップ（散布図）。 |
| `Docs/model_character_comparison.png` | 22個（モデルベース）の「記憶力」と「エネルギー」の比較マップ。 |
| `Docs/primitive_matching_report.csv` | オリジナルと合成モデルの照合精度をまとめた数値レポート。 |
| `Docs/DATASET_LIST_JP.md` | データセットの定義と概要。 |
| `Docs/PROJECT_RESOURCES_LIST_JP.md` | 本ファイル（リソース全量リスト）。 |
| `Docs/Unified_PKGF_Theory.md` | PKGF（Parallel Key Geometric Flow）の統合理論文書。 |
| `Docs/PKGF_Academic_Paper_jp.md` | 学術論文（日本語版）。 |
| `Docs/PKGF_Academic_Paper_en.md` | 学術論文（英語版）。 |
