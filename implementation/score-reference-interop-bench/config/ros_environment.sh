# The one ROS 2 environment of every ROS 2 process on the bench host
# (adapterAbortConditions of the model): Autoware, the ROS 2 processes of the
# middleware integration layer, and the ros2 command line tools with their
# daemon. Source it with bash after /opt/ros/humble/setup.bash, before the
# first ros2 command, so a daemon starts in it too. The CI runtime jobs source
# it for the adapter, the observer, the other participants of the startup
# probe and the ros2 command line. The Launch Manager passes a component only
# the variables of its configuration, so launch-manager/launch_manager_config.json
# carries the same values for the adapter and the health proxy node.
#
# - RMW_IMPLEMENTATION: rmw_cyclonedds_cpp. The adapter links baselibs'
#   abort override, and Fast DDS 2.6 throws and catches on its normal
#   startup path, so the adapter aborts under rmw_fastrtps_cpp (startup
#   probe of the bench).
# - CYCLONEDDS_URI: cyclonedds.xml next to this file. It keeps DDS on the
#   loopback interface without multicast and sets MaxAutoParticipantIndex to
#   120, as the AEBS Autoware benches do.
# - ROS_DOMAIN_ID: 91, as the AEBS Autoware benches.
# - ROS_LOCALHOST_ONLY: unset, as in the AEBS Autoware benches;
#   cyclonedds.xml already selects the loopback interface, so one setting
#   holds that choice.
_de4sdv_score_bench_config=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://${_de4sdv_score_bench_config}/cyclonedds.xml"
export ROS_DOMAIN_ID=91
unset ROS_LOCALHOST_ONLY
unset _de4sdv_score_bench_config
