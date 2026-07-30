/*
 * DE4SDV shared ROS 2 message and port type definitions.
 *
 * These are generic ROS 2/DDS communication types reused across AEBS physical
 * realization, simulation deployment, and future middleware adapter increments.
 * Feature-specific message specializations stay in their feature files.
 */

package DE4SDV_ROS2Types {

  abstract item def ROS2TopicMessage {
    doc /* Base type for ROS 2 topic messages. Specialized per message type. */
  }

  port def ROS2TopicEndpoint {
    doc /* Base port for ROS 2 topic endpoints. */
  }

  port def ROS2TopicSubscription :> ROS2TopicEndpoint {
    doc /* ROS 2 topic subscription port (inbound). */
    in item payload : ROS2TopicMessage;
  }

  port def ROS2TopicPublication :> ROS2TopicEndpoint {
    doc /* ROS 2 topic publication port (outbound). */
    out item payload : ROS2TopicMessage;
  }
}
