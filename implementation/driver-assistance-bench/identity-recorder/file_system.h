// DE4SDV driver-assistance bench (INC-DRIVING-002): the identity recorder's view of the file system.
//
// The recorder only reads files and hashes them, and writes one record. Everything it reads goes through this
// interface, so the host's tests drive the whole resolution against an in-memory fake (tests/fake_file_system.h);
// PosixFileSystem is the real one. Hashing streams the file, since a CUDA library is hundreds of megabytes.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace de4sdv::driver_assistance::identity {

class FileSystem {
 public:
  virtual ~FileSystem() = default;
  // The whole file, following symbolic links. False when it is not a readable regular file.
  virtual bool ReadFile(const std::string& path, std::string* out) const = 0;
  // A regular file, after following symbolic links.
  virtual bool IsRegularFile(const std::string& path) const = 0;
  // The SHA-256 (hex) and the size of a regular file, following symbolic links.
  virtual bool HashFile(const std::string& path, std::string* sha256_hex, std::uint64_t* size) const = 0;
  // The names in a directory, sorted; empty when it is absent.
  virtual std::vector<std::string> ListDirectory(const std::string& directory) const = 0;
  // The target of a symbolic link as stored in the link; empty when path is not a link.
  virtual std::string LinkTarget(const std::string& path) const = 0;
};

class PosixFileSystem final : public FileSystem {
 public:
  bool ReadFile(const std::string& path, std::string* out) const override;
  bool IsRegularFile(const std::string& path) const override;
  bool HashFile(const std::string& path, std::string* sha256_hex, std::uint64_t* size) const override;
  std::vector<std::string> ListDirectory(const std::string& directory) const override;
  std::string LinkTarget(const std::string& path) const override;
};

// Path helpers, purely textual (no file system access).
std::string JoinPath(const std::string& directory, const std::string& name);
std::string ParentPath(const std::string& path);
bool IsAbsolutePath(const std::string& path);

}  // namespace de4sdv::driver_assistance::identity
