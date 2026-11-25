FROM osrf/ros:jazzy-desktop-full

# 対話プロンプトによるビルド停止を防ぐ
ENV DEBIAN_FRONTEND=noninteractive

# 開発・シミュレーションに必要な ROS 2 パッケージとツールを導入
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-ros-gz \
    ros-jazzy-xacro \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-tf2-tools \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 対話シェル起動時に ROS 2 とワークスペース環境、通信範囲を自動設定
RUN { \
    echo ""; \
    echo "# ROS 2 Jazzy およびワークスペース設定"; \
    echo "source /opt/ros/jazzy/setup.bash"; \
    echo "[ -f /root/ros2_ws/install/setup.bash ] && source /root/ros2_ws/install/setup.bash"; \
    echo "export ROS_DOMAIN_ID=11"; \
    echo "export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"; \
    } >> /etc/bash.bashrc

WORKDIR /root/ros2_ws

# コンテナイメージ単体でもパッケージを利用できるようワークスペースを複製・ビルド
COPY ros2_ws/src /root/ros2_ws/src
RUN bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install"
