"""Hesai JT128 ロボットを Gazebo Sim 上に起動する launch ファイル。"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    gazebo_share = Path(get_package_share_directory("jt128_gazebo"))
    ros_gz_sim_share = Path(get_package_share_directory("ros_gz_sim"))

    xacro_file = str(gazebo_share / "urdf" / "robot.urdf.xacro")
    world_file = str(gazebo_share / "worlds" / "world.sdf")
    bridge_config = str(gazebo_share / "config" / "jt128_bridge.yaml")
    rviz_config = str(gazebo_share / "rviz" / "robot.rviz")

    hz_arg = DeclareLaunchArgument("hz", default_value="10", description="スキャン周波数 [Hz] (10 または 20)")
    noise_arg = DeclareLaunchArgument("noise", default_value="true", description="Gaussian ノイズ有効化")
    imu_arg = DeclareLaunchArgument("imu", default_value="true", description="IMU センサ有効化")
    imu_hz_arg = DeclareLaunchArgument("imu_hz", default_value="200", description="IMU 更新周波数 (200 または 500 Hz)")
    imu_noise_arg = DeclareLaunchArgument("imu_noise", default_value="true", description="IMU ノイズ有効化")
    config_arg = DeclareLaunchArgument(
        "config",
        default_value=str(gazebo_share / "config" / "jt128.yaml"),
        description="YAML 設定ファイルパス（YAML のキーは hz / noise 引数より優先）",
    )
    headless_arg = DeclareLaunchArgument("headless", default_value="false", description="GUI なしで起動")
    rviz_arg = DeclareLaunchArgument("rviz", default_value="true", description="RViz2 を起動")

    hz = LaunchConfiguration("hz")
    noise = LaunchConfiguration("noise")
    imu = LaunchConfiguration("imu")
    imu_hz = LaunchConfiguration("imu_hz")
    imu_noise = LaunchConfiguration("imu_noise")
    config = LaunchConfiguration("config")
    headless = LaunchConfiguration("headless")
    rviz = LaunchConfiguration("rviz")

    # config が空でも安全に渡せるよう xacro の引数形式で展開する
    robot_description = ParameterValue(
        Command([
            "xacro ", xacro_file,
            " hz:=", hz,
            " noise:=", noise,
            " imu:=", imu,
            " imu_hz:=", imu_hz,
            " imu_noise:=", imu_noise,
            " config:=", config,
        ]),
        value_type=str,
    )

    gz_args = PythonExpression([
        "'-s -r --headless-rendering ' + '", world_file, "' if '",
        headless, "' == 'true' else '-r ' + '", world_file, "'",
    ])

    # Gazebo Sim 本体は既存の ros_gz_sim launch を利用し、package.xml 経由でリソースパスを解決する
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(ros_gz_sim_share / "launch" / "gz_sim.launch.py")),
        launch_arguments={"gz_args": gz_args}.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True,
        }],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-name", "robot",
            "-x", "0", "-y", "0", "-z", "0",
        ],
    )

    # /clock 発行元のブリッジには use_sim_time を設定しない
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        parameters=[{"config_file": bridge_config}],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(PythonExpression([
            "'", headless, "' == 'false' and '", rviz, "' == 'true'",
        ])),
    )

    return LaunchDescription([
        hz_arg,
        noise_arg,
        imu_arg,
        imu_hz_arg,
        imu_noise_arg,
        config_arg,
        headless_arg,
        rviz_arg,
        gz_sim,
        robot_state_publisher,
        spawn_robot,
        bridge,
        rviz_node,
    ])
