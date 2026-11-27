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

# コンテナ内のプロセスをホストのユーザーと同じ UID/GID で動かす
# （root で動かすと共有メモリのファイルが root 所有になり、ホストの ROS 2 や MATLAB が点群を受信できないため）
# ベースイメージにある ubuntu ユーザー（UID/GID 1000）を、ビルド引数の UID/GID に合わせて使う
ARG USER_UID=1000
ARG USER_GID=1000
ENV ROS2_WS=/home/ubuntu/ros2_ws
RUN if [ "${USER_GID}" != "1000" ]; then groupmod -o -g "${USER_GID}" ubuntu; fi \
    && if [ "${USER_UID}" != "1000" ]; then usermod -o -u "${USER_UID}" -g "${USER_GID}" ubuntu; fi \
    && mkdir -p "${ROS2_WS}" \
    && chown -R ubuntu:ubuntu /home/ubuntu

# 対話シェル起動時に ROS 2 とワークスペース環境、通信範囲を自動設定
RUN { \
    echo ""; \
    echo "# ROS 2 Jazzy およびワークスペース設定"; \
    echo "source /opt/ros/jazzy/setup.bash"; \
    echo "[ -f ${ROS2_WS}/install/setup.bash ] && source ${ROS2_WS}/install/setup.bash"; \
    echo "export ROS_DOMAIN_ID=11"; \
    echo "export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"; \
    } >> /etc/bash.bashrc

USER ubuntu
WORKDIR ${ROS2_WS}

# コンテナイメージ単体でもパッケージを利用できるようワークスペースを複製・ビルド
COPY --chown=ubuntu:ubuntu ros2_ws/src ${ROS2_WS}/src
RUN bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install"
