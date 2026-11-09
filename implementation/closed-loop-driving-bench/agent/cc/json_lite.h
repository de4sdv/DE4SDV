// Minimal read-only JSON value + parser (C++17, no dependencies).
//
// The adapter reads exactly one small document per run (the vehicle limits
// configuration, ICD section 5, extended with the longitudinal calibration
// table). This parser covers that document: objects, arrays, numbers,
// strings (with the usual escapes), booleans and null. Numbers are doubles;
// the configuration has no integer that needs exactness beyond 2^53.
#pragma once

#include <cstddef>
#include <string>
#include <utility>
#include <vector>

namespace de4sdv::driving::json {

class Parser;

class Value {
 public:
  enum class Type { kNull, kBool, kNumber, kString, kArray, kObject };

  Value() = default;

  Type type() const { return type_; }
  bool IsNull() const { return type_ == Type::kNull; }
  bool IsBool() const { return type_ == Type::kBool; }
  bool IsNumber() const { return type_ == Type::kNumber; }
  bool IsString() const { return type_ == Type::kString; }
  bool IsArray() const { return type_ == Type::kArray; }
  bool IsObject() const { return type_ == Type::kObject; }

  // Object member lookup; nullptr when absent or when this is not an object.
  const Value* Find(const std::string& key) const;

  // Array access; nullptr when out of range or when this is not an array.
  const Value* At(std::size_t index) const;
  std::size_t size() const { return items_.size(); }

  // Typed access with an explicit fallback; no exceptions.
  double AsNumber(double fallback) const { return type_ == Type::kNumber ? number_ : fallback; }
  bool AsBool(bool fallback) const { return type_ == Type::kBool ? boolean_ : fallback; }
  std::string AsString(const std::string& fallback) const {
    return type_ == Type::kString ? string_ : fallback;
  }
  const std::vector<Value>& items() const { return items_; }
  const std::vector<std::pair<std::string, Value>>& members() const { return members_; }

  // Parses a complete document. On failure returns a null value and sets
  // *error to "<message> at byte <n>"; *error may be nullptr.
  static Value Parse(const std::string& text, std::string* error);

 private:
  Type type_ = Type::kNull;
  bool boolean_ = false;
  double number_ = 0.0;
  std::string string_;
  std::vector<Value> items_;                                // arrays
  std::vector<std::pair<std::string, Value>> members_;      // objects

  friend class Parser;
};

}  // namespace de4sdv::driving::json
