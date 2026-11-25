# Hesai JT128 Gazebo Sim 用 ROS 2 パッケージ (`jt128_description` / `jt128_gazebo`)

Hesai JT128（3D LiDAR）を Gazebo Sim（Harmonic）および ROS 2（Jazzy）に簡単に追加するためのパッケージ群と、開発・実行用の Docker 環境一式です。
`jt128_description` は JT128 単体の設定・モデルのみを保持し、動作確認用ワールド・ロボット・launch・RViz 設定は `jt128_gazebo` へ分離しています。

---

## 1. ディレクトリ構成

```text
.
├── Dockerfile
├── docker-compose.yml
├── README.md
└── ros2_ws/
    └── src/
        ├── jt128_description/           # JT128 本体の URDF/xacro・メッシュ・モデルのみ
        │   ├── CMakeLists.txt
        │   ├── package.xml
        │   ├── meshes/
        │   │   └── JT128_visual.dae
        │   ├── models/
        │   │   └── jt128/
        │   │       ├── model.config
        │   │       └── model.sdf
        │   └── urdf/
        │       └── JT128.urdf.xacro
        └── jt128_gazebo/                # Gazebo Sim 動作確認・設定用パッケージ
            ├── CMakeLists.txt
            ├── package.xml
            ├── config/
            │   ├── jt128.yaml               # センサ設定（起動時に読み込み）
            │   └── jt128_bridge.yaml        # ros_gz_bridge 用トピック設定
            ├── launch/
            │   └── gazebo.launch.py
            ├── rviz/
            │   └── robot.rviz
            ├── urdf/
            │   └── robot.urdf.xacro
            └── worlds/
                └── world.sdf
```

---

## 2. コンテナのビルドと起動手順

### 前提条件
- Docker / Docker Compose が利用可能であること
- NVIDIA GPU 利用時は NVIDIA Container Toolkit が導入されていること（Intel / AMD GPU を使用する場合は [docker-compose.yml](docker-compose.yml) の `deploy` を外し、コメント記載の `/dev/dri:/dev/dri` を有効化してください）

### 手順

1. GUI（Gazebo / RViz2）を表示する場合は、ホスト側で X11 接続を許可します。
   ```bash
   xhost +local:docker
   ```
2. コンテナをビルドして起動します（ビルド時にコンテナイメージ内の `/root/ros2_ws` へも `src/` の複製と `colcon build --symlink-install` が行われます）。
   ```bash
   docker compose build
   docker compose up -d
   ```
3. コンテナに入って確認・再ビルドします（`docker compose up -d` 時はホスト側の `./ros2_ws` が `/root/ros2_ws` にマウントされるため、ソース変更後に再ビルドしてください）。
   ```bash
   docker compose exec jt128_sim bash
   colcon build --symlink-install
   source /root/ros2_ws/install/setup.bash
   ```

> [!NOTE]
> `docker-compose.yml` は `network_mode: host` を使用し、`ROS_DOMAIN_ID=11` および `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` を設定しています。`LOCALHOST` は同一マシン内への限定であり、ホストプロセスとの隔離ではありません。そのため、**同じホスト上で同じ `ROS_DOMAIN_ID=11` を持つ他プロセスとも通信します**。

---

## 3. 使い方

### 3.1 シミュレーションの起動 (`jt128_gazebo`)

- **GUI あり（Gazebo + RViz2）**
  ```bash
  ros2 launch jt128_gazebo gazebo.launch.py
  ```
- **ヘッドレス実行（GUI なし・RViz2 なし）**
  ```bash
  ros2 launch jt128_gazebo gazebo.launch.py headless:=true
  ```
- **設定ファイルを指定して起動**
  ```bash
  ros2 launch jt128_gazebo gazebo.launch.py headless:=true \
    config:=/path/to/your_config.yaml
  ```

### 3.2 `gazebo.launch.py` の引数一覧

| 引数 | 既定値 | 内容 |
|---|---|---|
| `hz` | `10` | `xacro` の `hz` に渡す（`10` または `20`） |
| `noise` | `true` | `xacro` の `noise` に渡す（`true` / `false`） |
| `config` | `config/jt128.yaml`（インストール先） | `xacro` の `config`（YAML ファイルパス）に渡す |
| `headless` | `false` | `true` なら `gz sim -s -r --headless-rendering` で起動し RViz2 を起動しない |
| `rviz` | `true` | `false` なら RViz2 を起動しない（`headless:=true` 時は常に起動しない） |

既定で `jt128.yaml` を読み込むため、YAML に書かれたキーは `hz:=` / `noise:=` より優先されます。引数で切り替える場合は `config:=''` を併せて指定してください。

### 出力トピック

| トピック | 型 | 内容 |
|---|---|---|
| `/jt128/points` | `sensor_msgs/msg/PointCloud2` | 点群（`frame_id`: `jt128`） |
| `/clock` | `rosgraph_msgs/msg/Clock` | シミュレーション時刻 |

### 3.3 ロボット URDF への組み込み (`jt128_description`)

自身のロボットの `.urdf.xacro` に以下を記述するだけで取り付けられます。

```xml
<xacro:include filename="$(find jt128_description)/urdf/JT128.urdf.xacro"/>

<xacro:JT128 parent="base_link">
  <origin xyz="0 0 0.2" rpy="0 0 0"/>
</xacro:JT128>
```

#### マクロ引数一覧

| 引数 | 既定値 | 内容 |
|---|---|---|
| `parent` | `base_link` | 取り付け先リンク名 |
| `name` | `jt128` | リンク名・点群 `frame_id` の基準 |
| `topic` | `jt128/scan` | Gazebo 側トピック名（点群は `${topic}/points` に出力） |
| `hz` | `10` | スキャン周波数 `10` または `20` [Hz]（10→900点/周、20→450点/周） |
| `noise` | `true` | `false` のとき `<noise>` ブロックを出力しない |
| `noise_stddev` | `0.02` | Gaussian ノイズの標準偏差 [m]（`mean=0.0`） |
| `scan_z` | `0.04784` | 筐体底面中心からスキャン中心までの高さ [m] |
| `config` | `''` | YAML 設定ファイルのパス（空文字の場合は使用しない） |

#### YAML（`config` 引数）の仕様と優先順位
- 使用可能なキーは `hz`、`noise`、`noise_stddev` の **3 つのみ**です（未対応キーや存在しないファイル、`hz` が 10/20 以外の値はエラーで停止します）。
- 優先順位は **YAML 内のキー > マクロの引数** です。YAML 内で省略されたキーはマクロ引数の値で補われます。

#### ブリッジ設定の注意
[config/jt128_bridge.yaml](ros2_ws/src/jt128_gazebo/config/jt128_bridge.yaml) は YAML 仕様上変数展開ができないため、既定のトピック名（`jt128/scan/points` → `jt128/points`）に固定しています。マクロの `topic` を変更した場合は、ブリッジ YAML の `gz_topic_name` も合わせて変更してください。`name` を変更した場合はリンク名や点群の `frame_id` が変わりますが、トピック名は変わりません。

### 3.4 Gazebo world への単体設置 (`jt128_description`)

`jt128_description` には、ロボット URDF に組み込まず LiDAR 単体で使う Gazebo モデルも含まれています。world の `</world>` の直前に次を追加すると、原点から `z=0.2 m` の位置に設置できます。

```xml
<include>
  <uri>model://jt128</uri>
  <name>jt128</name>
  <pose>0 0 0.2 0 0 0</pose>
</include>
```

通常の `gz sim` から起動する場合は、モデルとメッシュの URI を解決できるよう、ビルド済みワークスペースを source したシェルでリソースパスを設定します。

```bash
JT128_SHARE="$(ros2 pkg prefix --share jt128_description)"
export GZ_SIM_RESOURCE_PATH="${JT128_SHARE}/models:${JT128_SHARE}/..${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
gz sim /path/to/your_world.sdf
```

このスタンドアロンモデルのスキャン周波数やノイズは `models/jt128/model.sdf` に設定されています。URDF マクロの `hz`、`noise`、YAML 引数は適用されません。また、単体モデルを world に読み込むだけでは ROS 2 ブリッジは起動しません。ROS 2 へ点群を配信する場合は、`ros_gz_bridge` を別途起動してください。

---

## 4. 既知の制限・近似

- **垂直角の均等角近似**: 実機の JT128 は垂直チャンネル角が不均等であり、マニュアル上の角度は平面への投影値ですが、本パッケージでは Gazebo `gpu_lidar` の仕様に合わせて `-4.4°〜90.5°` を 128 等分（約 `0.747°` 刻み）の均等角で近似しています。
- **`ring` 情報の非出力**: Gazebo Sim 標準の `gpu_lidar`（`PointCloudPacked`）はチャンネル番号（`ring` フィールド）を出力しないため、`/jt128/points` には `ring` は含まれません。
- **accuracy（系統誤差）**: 仕様の accuracy（±3 cm）はモデル化せず、precision（標準偏差 2 cm, `mean=0.0`）のみを Gaussian ノイズで模擬しています。
