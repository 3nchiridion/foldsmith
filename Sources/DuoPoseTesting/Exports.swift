// DuoPoseTesting is the harness a test target links: the detectors and pose geometry (DuoDetectors, re-exported) plus
// SnapshotTesting for the in-process size check (see HarnessCapability). duo-detect links DuoDetectors alone, because
// SnapshotTesting brings in the Testing framework, which exists only under a test runner.
@_exported import DuoDetectors
