cmake_minimum_required(VERSION 3.8)
project(mov_navigation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  urdf
  worlds
  launch
  scripts
  rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
