/*
 * Synthetic fixture for the viewer's framed-concern tests.
 * Hand-authored test data — NOT a copy of any real DE4SDV model file.
 */

package FramesFeature {
  private import Views::*;

  concern alphaConcern;
  concern betaConcern;
  concern gammaConcern;

  viewpoint def PlainFramingViewpoint {
    doc /* SAF Frames Domain: Frames Viewpoint. Aspect: Test & Sample */
  }

  viewpoint def BaseFramingViewpoint {
    frame concern baseConcern : BaseConcern;
  }

  viewpoint def MidFramingViewpoint :> BaseFramingViewpoint {
    frame concern midConcern : MidConcern;
  }

  viewpoint def UnframedViewpoint;

  // three own frames: the plain form, the `frame concern` form, the plain form
  view severalOwnFramesView {
    doc /* Synthetic view with three own frames. */
    viewpoint selected : PlainFramingViewpoint {
      frame alphaConcern;
      frame concern betaConcern : BetaConcern;
      frame gammaConcern;
    }
    expose FramesFeature::*;
    render asTreeDiagram;
  }

  // `frame` in a doc comment, a block comment and a line comment is no frame
  view commentFramesView {
    doc /* frame ghostConcern; */
    /* frame blockGhostConcern; */
    viewpoint selected : PlainFramingViewpoint {
      // frame lineGhostConcern;
      frame alphaConcern;
    }
    expose FramesFeature::*;
  }

  view noFramesView {
    viewpoint selected : UnframedViewpoint {
    }
    expose FramesFeature::*;
  }

  view inheritedOnlyView {
    viewpoint selected : BaseFramingViewpoint {
    }
    expose FramesFeature::*;
  }

  view inheritedAndOwnView {
    viewpoint selected : MidFramingViewpoint {
      frame alphaConcern;
    }
    expose FramesFeature::*;
  }

  view reframedInheritedView {
    viewpoint selected : BaseFramingViewpoint {
      frame baseConcern;
    }
    expose FramesFeature::*;
  }
}
