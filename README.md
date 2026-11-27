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
            │   ├── fastdds_shm.xml          # Fast DDS 共有メモリ設定（docker-compose.yml から読み込み）
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
2. コンテナをビルドして起動します（ビルド時にコンテナイメージ内の `/home/ubuntu/ros2_ws` へも `src/` の複製と `colcon build --symlink-install` が行われます）。
   ```bash
   docker compose build
   docker compose up -d
   ```
   コンテナ内のプロセスは root ではなく `ubuntu` ユーザー（既定 UID/GID 1000）で動作します。ホストのユーザーの UID/GID（`id -u` / `id -g`）が 1000 以外の場合は、合わせてビルドしてください（理由は後述の共有メモリ設定を参照）。
   ```bash
   HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose build
   ```
3. コンテナに入って確認・再ビルドします（`docker compose up -d` 時はホスト側の `./ros2_ws` が `/home/ubuntu/ros2_ws` にマウントされるため、ソース変更後に再ビルドしてください）。
   ```bash
   docker compose exec jt128_sim bash
   colcon build --symlink-install
   source /home/ubuntu/ros2_ws/install/setup.bash
   ```
   `apt install` など管理者権限が必要な作業は `docker compose exec -u root jt128_sim bash` で入って行います。以前の root で動作する版でビルドした `ros2_ws/build`・`install`・`log` が残っている場合は、root 所有のため `sudo rm -rf ros2_ws/build ros2_ws/install ros2_ws/log` で削除してから再ビルドしてください。

> [!NOTE]
> `docker-compose.yml` は `network_mode: host` を使用し、`ROS_DOMAIN_ID=11` および `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` を設定しています。`LOCALHOST` は同一マシン内への限定であり、ホストプロセスとの隔離ではありません。そのため、**同じホスト上で同じ `ROS_DOMAIN_ID=11` を持つ他プロセスとも通信します**。

### 点群通信の共有メモリ設定（Fast DDS）

JT128 の点群は 1 メッセージ約 1.8 MB（20 Hz）あり、Fast DDS 既定の共有メモリ（SHM）セグメント 512 KB に収まらず分割送信されます。その結果、BEST_EFFORT 購読では約半数が欠落し（Jazzy の `ros2 topic hz` は BEST_EFFORT 固定のため約 9 Hz と表示）、RELIABLE 購読でも遅延が 20〜35 ms に増えます。
そこで [fastdds_shm.xml](ros2_ws/src/jt128_gazebo/config/fastdds_shm.xml) でセグメントを 32 MB に拡大し、[docker-compose.yml](docker-compose.yml) の `FASTRTPS_DEFAULT_PROFILES_FILE` で読み込んでいます（変更後は `docker compose up -d` でコンテナを再作成すると反映されます）。

| 実測（20 Hz・1.8 MB/メッセージ） | 既定 | 本設定 |
|---|---|---|
| BEST_EFFORT 購読の受信周期 | 約 10 Hz（約 49% 欠落） | 19.8 Hz（欠落 0） |
| RELIABLE 購読の平均遅延 | 約 24 ms | 約 0.8 ms |

- 送信側（本コンテナの `ros_gz_bridge`）の設定で効くため、受信側の変更は不要です。対象は同じ `/dev/shm` を共有する Fast DDS（`rmw_fastrtps_cpp`）のプロセスです（`ipc: host` のコンテナなど）。
- コンテナ内のプロセスはホストと同じ UID で動作するため、ホストの一般ユーザーのプロセス（ROS 2 CLI・RViz2・MATLAB R2026a など）も SHM で受信できます（実測でホストの ROS 2・MATLAB R2026a とも約 19.7 Hz・欠落 0）。**UID が異なると SHM ファイル（権限 `0644`）を開けず、点群が 1 通も届きません**。たとえば、コンテナを root で動かした場合がこれに当たります。
- `network_mode: host` で IPC を共有しないコンテナも受信できません。Jazzy の `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` では rmw_fastrtps が SHM を必ず有効にするため（`FASTDDS_BUILTIN_TRANSPORTS=UDPv4` も無効）、`ipc: host` などで `/dev/shm` を共有してください。
- XML で `maxMessageSize` を `segment_size` より大きくすると SHM が無効になり、UDP のみの通信になります。

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
| `imu` | `true` | IMU を有効化（`false` で IMU リンク・センサを出力しない） |
| `imu_hz` | `200` | IMU 更新周波数（`200` または `500` Hz）。YAML の `imu_hz` が優先 |
| `imu_noise` | `true` | IMU ノイズを有効化。YAML の `imu_noise` が優先 |
| `config` | `config/jt128.yaml`（インストール先） | `xacro` の `config`（YAML ファイルパス）に渡す |
| `headless` | `false` | `true` なら `gz sim -s -r --headless-rendering` で起動し RViz2 を起動しない |
| `rviz` | `true` | `false` なら RViz2 を起動しない（`headless:=true` 時は常に起動しない） |

既定で `jt128.yaml` を読み込むため、YAML に書かれたキーは `hz:=` / `noise:=` より優先されます。引数で切り替える場合は `config:=''` を併せて指定してください。

### 出力トピック

| トピック | 型 | 内容 |
|---|---|---|
| `/jt128/points` | `sensor_msgs/msg/PointCloud2` | 点群（`frame_id`: `jt128`） |
| `/jt128/imu` | `sensor_msgs/msg/Imu` | 内蔵 IMU（既定 200 Hz、`frame_id`: `jt_128_imu`） |
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
| `imu` | `true` | IMU を有効化するか |
| `imu_topic` | `jt128/imu` | Gazebo 側 IMU トピック |
| `imu_hz` | `200` | IMU 更新周波数 `200` または `500` [Hz] |
| `imu_noise` | `true` | IMU ノイズを有効化するか |

#### YAML（`config` 引数）の仕様と優先順位
- 使用可能なキーは `hz`、`noise`、`noise_stddev`、`imu_hz`、`imu_noise` です（未対応キー、存在しないファイル、範囲外の周波数はエラーで停止します）。
- 優先順位は **YAML 内のキー > マクロの引数** です。YAML 内で省略されたキーはマクロ引数の値で補われます。

#### ブリッジ設定の注意
[config/jt128_bridge.yaml](ros2_ws/src/jt128_gazebo/config/jt128_bridge.yaml) は YAML 仕様上変数展開ができないため、既定のトピック名（`jt128/scan/points` → `jt128/points`、`jt128/imu`）に固定しています。マクロの `topic` または `imu_topic` を変更した場合は、ブリッジ YAML の `gz_topic_name` も合わせて変更してください。`name` を変更した場合はリンク名や点群の `frame_id` が変わりますが、トピック名は変わりません。

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
- **IMU 近似**: 取り付けオフセット `(0.0076, -0.01367, -0.01274) m` は FAST-LIO extrinsic からの暫定推定です。User Manual Figure 5 の寸法・軸向きと照合してください。IMU のノイズ・バイアス値も一般的な MEMS IMU を参考にした推定値で、実機 Allan 分散による同定値ではありません。
