// The real file system of the identity recorder (POSIX and std::filesystem, C++17).
#include "file_system.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

#include "sha256.h"

namespace de4sdv::driver_assistance::identity {

namespace fs = std::filesystem;

bool PosixFileSystem::ReadFile(const std::string& path, std::string* out) const {
  if (!IsRegularFile(path)) return false;
  std::FILE* file = std::fopen(path.c_str(), "rb");
  if (file == nullptr) return false;
  std::string data;
  char buffer[65536];
  std::size_t got = 0;
  while ((got = std::fread(buffer, 1, sizeof buffer, file)) > 0) data.append(buffer, got);
  const bool ok = std::ferror(file) == 0;
  std::fclose(file);
  if (ok) *out = std::move(data);
  return ok;
}

bool PosixFileSystem::IsRegularFile(const std::string& path) const {
  std::error_code error;
  return fs::is_regular_file(fs::path(path), error);
}

bool PosixFileSystem::HashFile(const std::string& path, std::string* sha256_hex, std::uint64_t* size) const {
  if (!IsRegularFile(path)) return false;
  std::FILE* file = std::fopen(path.c_str(), "rb");
  if (file == nullptr) return false;
  Sha256 hash;
  std::uint64_t total = 0;
  static thread_local std::vector<char> buffer(1 << 20);
  std::size_t got = 0;
  while ((got = std::fread(buffer.data(), 1, buffer.size(), file)) > 0) {
    hash.Update(buffer.data(), got);
    total += got;
  }
  const bool ok = std::ferror(file) == 0;
  std::fclose(file);
  if (!ok) return false;
  *sha256_hex = hash.HexDigest();
  *size = total;
  return true;
}

std::vector<std::string> PosixFileSystem::ListDirectory(const std::string& directory) const {
  std::vector<std::string> names;
  std::error_code error;
  fs::directory_iterator it(fs::path(directory), error);
  if (error) return names;
  for (const fs::directory_entry& entry : it) names.push_back(entry.path().filename().string());
  std::sort(names.begin(), names.end());
  return names;
}

std::string PosixFileSystem::LinkTarget(const std::string& path) const {
  std::error_code error;
  if (!fs::is_symlink(fs::symlink_status(fs::path(path), error))) return "";
  const fs::path target = fs::read_symlink(fs::path(path), error);
  return error ? std::string() : target.string();
}

std::string JoinPath(const std::string& directory, const std::string& name) {
  if (directory.empty()) return name;
  if (IsAbsolutePath(name)) return name;
  if (directory.back() == '/') return directory + name;
  return directory + "/" + name;
}

std::string ParentPath(const std::string& path) {
  std::string p = path;
  while (p.size() > 1 && p.back() == '/') p.pop_back();
  const std::size_t slash = p.rfind('/');
  if (slash == std::string::npos) return ".";
  if (slash == 0) return "/";
  return p.substr(0, slash);
}

bool IsAbsolutePath(const std::string& path) { return !path.empty() && path[0] == '/'; }

}  // namespace de4sdv::driver_assistance::identity
