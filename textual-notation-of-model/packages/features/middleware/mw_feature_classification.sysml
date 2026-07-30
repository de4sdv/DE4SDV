/*
 * DE4SDV middleware feature/common-capability classification model slice.
 *
 * INC-MW-003 classifies each middleware integration element as a feature,
 * common capability, constraint, or evidence capability per the DE4SDV
 * feature/common-capability rule (ISO/IEC 26580-aligned). It confirms the
 * classification hypothesis from INC-MW-002.
 *
 * Features (middleware selection, application selection) are already modeled
 * as native SysML v2 variation/variant in the SDV platform stack
 * (DE4SDV_SDVPlatformStack). This file does NOT duplicate them. It records
 * only the common capabilities that are not variation points and the
 * classification concern for review.
 *
 * This increment does NOT define requirements, functional behavior, logical
 * architecture, or physical/software realization.
 */

package DE4SDV_MWFeatureClassification {
  package Features {
    package Middleware {
      package FeatureClassification {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import DE4SDV_SDVPlatformStack::*;

        /*
         * Classification concern: reviewers need to see common capabilities
         * separated from features and variation points.
         */
        concern productLineCapabilityClassificationConcern : ProductLineCapabilityClassificationConcern {
          doc /*
           * Reviewers need middleware scope elements to distinguish common
           * product-line capabilities from features and variation points
           * before downstream functional modeling starts. Features are the
           * variation points already in the SDV platform stack; common
           * capabilities are the parts listed here that are required for
           * any app+middleware combination.
           */
          subject;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        /*
         * Common capabilities — required for any app+middleware combination.
         * Not features: they do not distinguish member products.
         * These are NOT variation points in the SDV platform stack.
         */
        part adapterLayer : CommonProductLineCapability {
          doc /*
           * The application-middleware adapter layer is a common capability.
           * Every (application, middleware) pair requires an adapter to
           * translate between incompatible communication paradigms
           * (ROS 2/DDS vs VSIDL/LoLa/SOME/IP). The adapter does not
           * distinguish member products — it is present whenever middleware
           * is not "none" and absent when it is. The specific adapter
           * variant follows from the (application, middleware) feature
           * pair — see the adapter variation in DE4SDV_SDVPlatformStack.
           */
        }

        part signalAccessCapability : CommonProductLineCapability {
          doc /*
           * The capability to exchange vehicle signals through the
           * middleware is a common capability. It is required whenever
           * an ADAS application and a vehicle-level middleware are both
           * selected. Does not distinguish member products.
           */
        }

        part lifecycleCoordinationCapability : CommonProductLineCapability {
          doc /*
           * Lifecycle coordination (startup, shutdown, suspend, resume)
           * through the middleware is a common capability. Required for
           * all middleware-integrated products. Does not distinguish
           * member products.
           */
        }

        part healthMonitoringCapability : CommonProductLineCapability {
          doc /*
           * Health monitoring and fault detection through the middleware
           * is a common capability. Required for all middleware-integrated
           * products.
           */
        }

        part diagnosticAccessCapability : CommonProductLineCapability {
          doc /*
           * Authenticated diagnostic access through the middleware is a
           * common capability. Does not distinguish member products.
           */
        }

        part updateCoordinationCapability : CommonProductLineCapability {
          doc /*
           * OTA software update coordination through the middleware is a
           * common capability. Does not distinguish member products.
           */
        }

        /*
         * Deferred scope — not classified in this increment.
         */
        part safetyPathDecision : DeferredProductLineScope {
          doc /*
           * The decision about which emergency intervention path to
           * realize (through safety-certified middleware partition vs
           * direct vehicle-command gate) is deferred to INC-MW-004
           * (needs) and INC-MW-005 (requirements).
           */
        }

        part securityTrustBoundary : DeferredProductLineScope {
          doc /*
           * The security and trust boundary for middleware communication
           * (DICE identity, attestation, VLAN segmentation) is not yet
           * classified. Deferred to a security-focused increment or
           * INC-MW-005.
           */
        }

        /*
         * View
         */
        view mwProductLineClassificationView {
          viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
            frame productLineCapabilityClassificationConcern;
          }

          expose FeatureClassification::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
