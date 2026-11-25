cmake_minimum_required(VERSION 3.8)
project(jt128_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  meshes
  models
  urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
