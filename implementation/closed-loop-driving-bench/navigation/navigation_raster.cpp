#include "navigation_raster.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <charconv>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <sstream>
#include <utility>

// The pinned upstream native rasterizer, built unmodified from
// .upstream/Model/navigation/native/navigation_rasterizer.cpp.
#include "navigation_rasterizer.h"

namespace de4sdv::driving::navigation {
namespace {

// ------------------------------------------------------------------ JSON

struct JsonValue {
  enum class Type { kNull, kBool, kNumber, kString, kArray, kObject };
  Type type = Type::kNull;
  bool boolean = false;
  double number = 0.0;
  std::string text;
  std::vector<JsonValue> array;
  std::vector<std::pair<std::string, JsonValue>> object;

  const JsonValue* Find(const std::string& key) const {
    for (const auto& entry : object) {
      if (entry.first == key) return &entry.second;
    }
    return nullptr;
  }
};

class JsonParser {
 public:
  explicit JsonParser(const std::string& text) : text_(text) {}

  bool Parse(JsonValue* out, std::string* error) {
    if (!ParseValue(out, 0)) {
      *error = error_;
      return false;
    }
    SkipWhitespace();
    if (position_ != text_.size()) {
      *error = Describe("trailing characters");
      return false;
    }
    return true;
  }

 private:
  std::string Describe(const std::string& what) const {
    std::ostringstream stream;
    stream << "JSON " << what << " at offset " << position_;
    return stream.str();
  }

  void SkipWhitespace() {
    while (position_ < text_.size()) {
      const char c = text_[position_];
      if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
        ++position_;
      } else {
        break;
      }
    }
  }

  bool Fail(const std::string& what) {
    error_ = Describe(what);
    return false;
  }

  bool ParseValue(JsonValue* out, int depth) {
    if (depth > 64) return Fail("nesting too deep");
    SkipWhitespace();
    if (position_ >= text_.size()) return Fail("unexpected end");
    const char c = text_[position_];
    switch (c) {
      case '{':
        return ParseObject(out, depth);
      case '[':
        return ParseArray(out, depth);
      case '"':
        out->type = JsonValue::Type::kString;
        return ParseString(&out->text);
      case 't':
        if (text_.compare(position_, 4, "true") != 0) return Fail("bad literal");
        position_ += 4;
        out->type = JsonValue::Type::kBool;
        out->boolean = true;
        return true;
      case 'f':
        if (text_.compare(position_, 5, "false") != 0) return Fail("bad literal");
        position_ += 5;
        out->type = JsonValue::Type::kBool;
        out->boolean = false;
        return true;
      case 'n':
        if (text_.compare(position_, 4, "null") != 0) return Fail("bad literal");
        position_ += 4;
        out->type = JsonValue::Type::kNull;
        return true;
      default:
        return ParseNumber(out);
    }
  }

  bool ParseNumber(JsonValue* out) {
    const std::size_t start = position_;
    if (position_ < text_.size() &&
        (text_[position_] == '-' || text_[position_] == '+')) {
      ++position_;
    }
    bool digits = false;
    while (position_ < text_.size() && text_[position_] >= '0' &&
           text_[position_] <= '9') {
      ++position_;
      digits = true;
    }
    if (position_ < text_.size() && text_[position_] == '.') {
      ++position_;
      while (position_ < text_.size() && text_[position_] >= '0' &&
             text_[position_] <= '9') {
        ++position_;
        digits = true;
      }
    }
    if (!digits) return Fail("bad number");
    if (position_ < text_.size() &&
        (text_[position_] == 'e' || text_[position_] == 'E')) {
      ++position_;
      if (position_ < text_.size() &&
          (text_[position_] == '-' || text_[position_] == '+')) {
        ++position_;
      }
      bool exponent_digits = false;
      while (position_ < text_.size() && text_[position_] >= '0' &&
             text_[position_] <= '9') {
        ++position_;
        exponent_digits = true;
      }
      if (!exponent_digits) return Fail("bad exponent");
    }
    const char* first = text_.data() + start;
    const char* last = text_.data() + position_;
    double value = 0.0;
    const auto result = std::from_chars(first, last, value);
    if (result.ec != std::errc() || result.ptr != last) {
      return Fail("number out of range");
    }
    out->type = JsonValue::Type::kNumber;
    out->number = value;
    return true;
  }

  static void AppendUtf8(std::uint32_t code_point, std::string* out) {
    if (code_point <= 0x7F) {
      out->push_back(static_cast<char>(code_point));
    } else if (code_point <= 0x7FF) {
      out->push_back(static_cast<char>(0xC0 | (code_point >> 6)));
      out->push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    } else if (code_point <= 0xFFFF) {
      out->push_back(static_cast<char>(0xE0 | (code_point >> 12)));
      out->push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
      out->push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    } else {
      out->push_back(static_cast<char>(0xF0 | (code_point >> 18)));
      out->push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3F)));
      out->push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
      out->push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
    }
  }

  bool ParseHex4(std::uint32_t* out) {
    if (position_ + 4 > text_.size()) return Fail("short \\u escape");
    std::uint32_t value = 0;
    for (int index = 0; index < 4; ++index) {
      const char c = text_[position_ + static_cast<std::size_t>(index)];
      value <<= 4;
      if (c >= '0' && c <= '9') {
        value |= static_cast<std::uint32_t>(c - '0');
      } else if (c >= 'a' && c <= 'f') {
        value |= static_cast<std::uint32_t>(c - 'a' + 10);
      } else if (c >= 'A' && c <= 'F') {
        value |= static_cast<std::uint32_t>(c - 'A' + 10);
      } else {
        return Fail("bad \\u escape");
      }
    }
    position_ += 4;
    *out = value;
    return true;
  }

  bool ParseString(std::string* out) {
    if (position_ >= text_.size() || text_[position_] != '"') {
      return Fail("expected string");
    }
    ++position_;
    out->clear();
    while (true) {
      if (position_ >= text_.size()) return Fail("unterminated string");
      const unsigned char c = static_cast<unsigned char>(text_[position_++]);
      if (c == '"') return true;
      if (c < 0x20) return Fail("control character in string");
      if (c != '\\') {
        out->push_back(static_cast<char>(c));
        continue;
      }
      if (position_ >= text_.size()) return Fail("unterminated escape");
      const char escape = text_[position_++];
      switch (escape) {
        case '"': out->push_back('"'); break;
        case '\\': out->push_back('\\'); break;
        case '/': out->push_back('/'); break;
        case 'b': out->push_back('\b'); break;
        case 'f': out->push_back('\f'); break;
        case 'n': out->push_back('\n'); break;
        case 'r': out->push_back('\r'); break;
        case 't': out->push_back('\t'); break;
        case 'u': {
          std::uint32_t code_point = 0;
          if (!ParseHex4(&code_point)) return false;
          if (code_point >= 0xD800 && code_point <= 0xDBFF &&
              position_ + 1 < text_.size() && text_[position_] == '\\' &&
              text_[position_ + 1] == 'u') {
            const std::size_t saved = position_;
            position_ += 2;
            std::uint32_t low = 0;
            if (!ParseHex4(&low)) return false;
            if (low >= 0xDC00 && low <= 0xDFFF) {
              code_point = 0x10000 + ((code_point - 0xD800) << 10) +
                           (low - 0xDC00);
            } else {
              position_ = saved;
            }
          }
          AppendUtf8(code_point, out);
          break;
        }
        default:
          return Fail("bad escape");
      }
    }
  }

  bool ParseArray(JsonValue* out, int depth) {
    ++position_;  // '['
    out->type = JsonValue::Type::kArray;
    out->array.clear();
    SkipWhitespace();
    if (position_ < text_.size() && text_[position_] == ']') {
      ++position_;
      return true;
    }
    while (true) {
      JsonValue element;
      if (!ParseValue(&element, depth + 1)) return false;
      out->array.push_back(std::move(element));
      SkipWhitespace();
      if (position_ >= text_.size()) return Fail("unterminated array");
      if (text_[position_] == ',') {
        ++position_;
        continue;
      }
      if (text_[position_] == ']') {
        ++position_;
        return true;
      }
      return Fail("expected ',' or ']'");
    }
  }

  bool ParseObject(JsonValue* out, int depth) {
    ++position_;  // '{'
    out->type = JsonValue::Type::kObject;
    out->object.clear();
    SkipWhitespace();
    if (position_ < text_.size() && text_[position_] == '}') {
      ++position_;
      return true;
    }
    while (true) {
      SkipWhitespace();
      std::string key;
      if (!ParseString(&key)) return false;
      SkipWhitespace();
      if (position_ >= text_.size() || text_[position_] != ':') {
        return Fail("expected ':'");
      }
      ++position_;
      JsonValue value;
      if (!ParseValue(&value, depth + 1)) return false;
      out->object.emplace_back(std::move(key), std::move(value));
      SkipWhitespace();
      if (position_ >= text_.size()) return Fail("unterminated object");
      if (text_[position_] == ',') {
        ++position_;
        continue;
      }
      if (text_[position_] == '}') {
        ++position_;
        return true;
      }
      return Fail("expected ',' or '}'");
    }
  }

  const std::string& text_;
  std::size_t position_ = 0;
  std::string error_;
};

// Field accessors with a readable path in every message.
std::string Join(const std::string& prefix, const std::string& key) {
  return prefix.empty() ? key : prefix + "." + key;
}

bool RequireObject(const JsonValue& value, const std::string& path,
                   std::string* error) {
  if (value.type != JsonValue::Type::kObject) {
    *error = path + ": expected an object";
    return false;
  }
  return true;
}

bool RequireNumber(const JsonValue& value, const std::string& path,
                   double* out, std::string* error) {
  if (value.type != JsonValue::Type::kNumber || !std::isfinite(value.number)) {
    *error = path + ": expected a finite number";
    return false;
  }
  *out = value.number;
  return true;
}

bool RequireString(const JsonValue& value, const std::string& path,
                   std::string* out, std::string* error) {
  if (value.type != JsonValue::Type::kString) {
    *error = path + ": expected a string";
    return false;
  }
  *out = value.text;
  return true;
}

bool RequireStringField(const JsonValue& object, const std::string& key,
                        const std::string& path, std::string* out,
                        std::string* error) {
  const JsonValue* value = object.Find(key);
  if (value == nullptr) {
    *error = path + ": missing";
    return false;
  }
  return RequireString(*value, path, out, error);
}

bool RequireArray(const JsonValue& value, const std::string& path,
                  std::string* error) {
  if (value.type != JsonValue::Type::kArray) {
    *error = path + ": expected an array";
    return false;
  }
  return true;
}

bool OptionalLevel(const JsonValue& object, const std::string& path,
                   std::int32_t* level, bool* level_valid, std::string* error) {
  *level = 0;
  *level_valid = false;
  const JsonValue* value = object.Find("level");
  if (value == nullptr || value->type == JsonValue::Type::kNull) return true;
  double number = 0.0;
  if (!RequireNumber(*value, Join(path, "level"), &number, error)) return false;
  *level = static_cast<std::int32_t>(std::llround(number));
  *level_valid = true;
  return true;
}

// [[x, y, z], ...] or [[x, y], ...] to 2D points, as upstream's _points does.
bool ParsePointList(const JsonValue& value, const std::string& path,
                    std::size_t minimum, std::vector<Point>* out,
                    std::string* error) {
  if (!RequireArray(value, path, error)) return false;
  if (value.array.size() < minimum) {
    *error = path + ": needs at least " + std::to_string(minimum) + " points";
    return false;
  }
  out->clear();
  out->reserve(value.array.size());
  for (std::size_t index = 0; index < value.array.size(); ++index) {
    const JsonValue& row = value.array[index];
    const std::string row_path = path + "[" + std::to_string(index) + "]";
    if (!RequireArray(row, row_path, error)) return false;
    if (row.array.size() != 2 && row.array.size() != 3) {
      *error = row_path + ": expected [x, y] or [x, y, z]";
      return false;
    }
    Point point{};
    if (!RequireNumber(row.array[0], row_path + "[0]", &point.x, error) ||
        !RequireNumber(row.array[1], row_path + "[1]", &point.y, error)) {
      return false;
    }
    out->push_back(point);
  }
  return true;
}

bool AppendPolygons(const JsonValue& root, const std::string& group,
                    std::int32_t channel, float width_m, MapData* map,
                    std::string* error) {
  const JsonValue* array = root.Find(group);
  if (array == nullptr) return true;
  if (!RequireArray(*array, group, error)) return false;
  for (std::size_t index = 0; index < array->array.size(); ++index) {
    const JsonValue& item = array->array[index];
    const std::string path = group + "[" + std::to_string(index) + "]";
    if (!RequireObject(item, path, error)) return false;
    const JsonValue* points = item.Find("points_enu_m");
    if (points == nullptr) {
      *error = path + ": missing points_enu_m";
      return false;
    }
    Primitive primitive;
    primitive.kind = PrimitiveKind::kPolygon;
    primitive.channel = channel;
    primitive.width_m = width_m;
    if (!ParsePointList(*points, path + ".points_enu_m", 3,
                        &primitive.points, error)) {
      return false;
    }
    if (!OptionalLevel(item, path, &primitive.level, &primitive.level_valid,
                       error)) {
      return false;
    }
    map->primitives.push_back(std::move(primitive));
  }
  return true;
}

bool AppendPolylines(const JsonValue& root, const std::string& group,
                     std::int32_t channel, float width_m, MapData* map,
                     std::string* error) {
  const JsonValue* array = root.Find(group);
  if (array == nullptr) return true;
  if (!RequireArray(*array, group, error)) return false;
  for (std::size_t index = 0; index < array->array.size(); ++index) {
    const JsonValue& item = array->array[index];
    const std::string path = group + "[" + std::to_string(index) + "]";
    if (!RequireObject(item, path, error)) return false;
    const JsonValue* points = item.Find("points_enu_m");
    if (points == nullptr) {
      *error = path + ": missing points_enu_m";
      return false;
    }
    Primitive primitive;
    primitive.kind = PrimitiveKind::kLine;
    primitive.channel = channel;
    primitive.width_m = width_m;
    if (!ParsePointList(*points, path + ".points_enu_m", 2, &primitive.points,
                        error)) {
      return false;
    }
    if (!OptionalLevel(item, path, &primitive.level, &primitive.level_valid,
                       error)) {
      return false;
    }
    map->primitives.push_back(std::move(primitive));
  }
  return true;
}

}  // namespace

// --------------------------------------------------------------- SHA-256

namespace {
namespace sha256_detail {

inline std::uint32_t RotateRight(std::uint32_t value, int bits) {
  return (value >> bits) | (value << (32 - bits));
}

constexpr std::array<std::uint32_t, 64> kRoundConstants = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU,
    0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U, 0xd807aa98U, 0x12835b01U,
    0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U,
    0xc19bf174U, 0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
    0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU, 0x983e5152U,
    0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U,
    0x06ca6351U, 0x14292967U, 0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU,
    0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U,
    0xd6990624U, 0xf40e3585U, 0x106aa070U, 0x19a4c116U, 0x1e376c08U,
    0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU,
    0x682e6ff3U, 0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
    0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U};

}  // namespace sha256_detail

std::string Sha256Hex(const std::string& data) {
  using namespace sha256_detail;
  std::array<std::uint32_t, 8> state = {0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U,
                                        0xa54ff53aU, 0x510e527fU, 0x9b05688cU,
                                        0x1f83d9abU, 0x5be0cd19U};
  std::vector<std::uint8_t> message(data.begin(), data.end());
  const std::uint64_t bit_length = static_cast<std::uint64_t>(data.size()) * 8U;
  message.push_back(0x80U);
  while (message.size() % 64 != 56) message.push_back(0U);
  for (int shift = 56; shift >= 0; shift -= 8) {
    message.push_back(static_cast<std::uint8_t>((bit_length >> shift) & 0xFFU));
  }
  std::array<std::uint32_t, 64> words{};
  for (std::size_t offset = 0; offset < message.size(); offset += 64) {
    for (std::size_t index = 0; index < 16; ++index) {
      const std::size_t base = offset + index * 4;
      words[index] = (static_cast<std::uint32_t>(message[base]) << 24) |
                     (static_cast<std::uint32_t>(message[base + 1]) << 16) |
                     (static_cast<std::uint32_t>(message[base + 2]) << 8) |
                     static_cast<std::uint32_t>(message[base + 3]);
    }
    for (std::size_t index = 16; index < 64; ++index) {
      const std::uint32_t s0 = RotateRight(words[index - 15], 7) ^
                               RotateRight(words[index - 15], 18) ^
                               (words[index - 15] >> 3);
      const std::uint32_t s1 = RotateRight(words[index - 2], 17) ^
                               RotateRight(words[index - 2], 19) ^
                               (words[index - 2] >> 10);
      words[index] = words[index - 16] + s0 + words[index - 7] + s1;
    }
    std::uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    std::uint32_t e = state[4], f = state[5], g = state[6], h = state[7];
    for (std::size_t index = 0; index < 64; ++index) {
      const std::uint32_t s1 =
          RotateRight(e, 6) ^ RotateRight(e, 11) ^ RotateRight(e, 25);
      const std::uint32_t choose = (e & f) ^ (~e & g);
      const std::uint32_t temp1 =
          h + s1 + choose + kRoundConstants[index] + words[index];
      const std::uint32_t s0 =
          RotateRight(a, 2) ^ RotateRight(a, 13) ^ RotateRight(a, 22);
      const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
      const std::uint32_t temp2 = s0 + majority;
      h = g;
      g = f;
      f = e;
      e = d + temp1;
      d = c;
      c = b;
      b = a;
      a = temp1 + temp2;
    }
    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
  }
  static const char* kHex = "0123456789abcdef";
  std::string hex;
  hex.reserve(64);
  for (const std::uint32_t word : state) {
    for (int shift = 28; shift >= 0; shift -= 4) {
      hex.push_back(kHex[(word >> shift) & 0xFU]);
    }
  }
  return hex;
}

}  // namespace

// ------------------------------------------------------------------ parsing

bool ParseMapJson(const std::string& text, MapData* map, std::string* error) {
  if (map == nullptr || error == nullptr) return false;
  JsonValue root;
  JsonParser parser(text);
  if (!parser.Parse(&root, error)) return false;
  if (!RequireObject(root, "map", error)) return false;

  const JsonValue* schema = root.Find("schema_version");
  if (schema == nullptr) {
    *error = "map.schema_version: missing";
    return false;
  }
  std::string schema_version;
  if (!RequireString(*schema, "schema_version", &schema_version, error)) {
    return false;
  }
  if (schema_version != "v1") {
    *error = "map.schema_version: unsupported " + schema_version;
    return false;
  }

  MapData parsed;
  if (!RequireStringField(root, "map_version", "map.map_version",
                          &parsed.map_version, error) ||
      !RequireStringField(root, "provider", "map.provider", &parsed.provider,
                          error)) {
    return false;
  }
  if (parsed.map_version.empty()) {
    *error = "map.map_version: must not be empty";
    return false;
  }
  const JsonValue* frame = root.Find("frame");
  if (frame == nullptr || !RequireObject(*frame, "frame", error)) {
    if (frame == nullptr) *error = "map.frame: missing";
    return false;
  }
  if (!RequireStringField(*frame, "frame_id", "frame.frame_id",
                          &parsed.frame_id, error)) {
    return false;
  }

  const JsonValue* bounds = root.Find("bounds_enu_m");
  if (bounds == nullptr || !RequireArray(*bounds, "bounds_enu_m", error)) {
    if (bounds == nullptr) *error = "map.bounds_enu_m: missing";
    return false;
  }
  if (bounds->array.size() != 4) {
    *error = "map.bounds_enu_m: expected four numbers";
    return false;
  }
  for (std::size_t index = 0; index < 4; ++index) {
    if (!RequireNumber(bounds->array[index],
                       "bounds_enu_m[" + std::to_string(index) + "]",
                       &parsed.bounds_enu_m[index], error)) {
      return false;
    }
  }
  if (!(parsed.bounds_enu_m[0] < parsed.bounds_enu_m[2]) ||
      !(parsed.bounds_enu_m[1] < parsed.bounds_enu_m[3])) {
    *error = "map.bounds_enu_m: must be (xmin,ymin,xmax,ymax) with extent";
    return false;
  }

  // Order of _map_primitive_specs: known map area first.
  {
    Primitive known_area;
    known_area.kind = PrimitiveKind::kPolygon;
    known_area.channel = static_cast<std::int32_t>(MapChannel::kKnownMapArea);
    known_area.width_m = 0.0F;
    const double x_min = parsed.bounds_enu_m[0];
    const double y_min = parsed.bounds_enu_m[1];
    const double x_max = parsed.bounds_enu_m[2];
    const double y_max = parsed.bounds_enu_m[3];
    known_area.points = {{x_min, y_min}, {x_max, y_min}, {x_max, y_max},
                         {x_min, y_max}};
    parsed.primitives.push_back(std::move(known_area));
  }

  if (!AppendPolygons(root, "drivable_polygons",
                      static_cast<std::int32_t>(MapChannel::kDrivableArea), 0.0F,
                      &parsed, error) ||
      !AppendPolylines(root, "lane_boundaries",
                       static_cast<std::int32_t>(MapChannel::kLaneBoundary),
                       1.0F, &parsed, error) ||
      !AppendPolylines(root, "lane_centerlines",
                       static_cast<std::int32_t>(MapChannel::kLaneCenterline),
                       1.0F, &parsed, error) ||
      !AppendPolygons(root, "intersection_polygons",
                      static_cast<std::int32_t>(MapChannel::kIntersection), 0.0F,
                      &parsed, error) ||
      !AppendPolygons(root, "crosswalk_polygons",
                      static_cast<std::int32_t>(MapChannel::kCrosswalk), 0.0F,
                      &parsed, error) ||
      !AppendPolylines(root, "stop_lines",
                       static_cast<std::int32_t>(MapChannel::kStopLine), 1.0F,
                       &parsed, error)) {
    return false;
  }

  // StaticTrafficSignal: one position, drawn as a 2 m disc (NAV_POINT).
  if (const JsonValue* signals = root.Find("static_traffic_signals")) {
    if (!RequireArray(*signals, "static_traffic_signals", error)) return false;
    for (std::size_t index = 0; index < signals->array.size(); ++index) {
      const JsonValue& item = signals->array[index];
      const std::string path =
          "static_traffic_signals[" + std::to_string(index) + "]";
      if (!RequireObject(item, path, error)) return false;
      const JsonValue* position = item.Find("position_enu_m");
      if (position == nullptr) {
        *error = path + ": missing position_enu_m";
        return false;
      }
      if (!RequireArray(*position, path + ".position_enu_m", error)) {
        return false;
      }
      if (position->array.size() != 2 && position->array.size() != 3) {
        *error = path + ".position_enu_m: expected [x, y] or [x, y, z]";
        return false;
      }
      Primitive primitive;
      primitive.kind = PrimitiveKind::kPoint;
      primitive.channel =
          static_cast<std::int32_t>(MapChannel::kStaticTrafficSignal);
      primitive.width_m = 2.0F;
      Point point{};
      if (!RequireNumber(position->array[0], path + ".position_enu_m[0]",
                         &point.x, error) ||
          !RequireNumber(position->array[1], path + ".position_enu_m[1]",
                         &point.y, error)) {
        return false;
      }
      primitive.points.push_back(point);
      if (!OptionalLevel(item, path, &primitive.level, &primitive.level_valid,
                         error)) {
        return false;
      }
      parsed.primitives.push_back(std::move(primitive));
    }
  }

  // DirectedLaneField: centre line whose heading fills channels 7/8/9.
  if (const JsonValue* fields = root.Find("directed_lane_fields")) {
    if (!RequireArray(*fields, "directed_lane_fields", error)) return false;
    for (std::size_t index = 0; index < fields->array.size(); ++index) {
      const JsonValue& item = fields->array[index];
      const std::string path =
          "directed_lane_fields[" + std::to_string(index) + "]";
      if (!RequireObject(item, path, error)) return false;
      const JsonValue* line = item.Find("centerline_enu_m");
      if (line == nullptr) {
        *error = path + ": missing centerline_enu_m";
        return false;
      }
      Primitive primitive;
      primitive.kind = PrimitiveKind::kDirectionLine;
      primitive.channel =
          static_cast<std::int32_t>(MapChannel::kTrafficDirectionValid);
      primitive.width_m = kRouteCorridorWidthM;
      if (!ParsePointList(*line, path + ".centerline_enu_m", 2,
                          &primitive.points, error)) {
        return false;
      }
      if (!OptionalLevel(item, path, &primitive.level, &primitive.level_valid,
                         error)) {
        return false;
      }
      parsed.primitives.push_back(std::move(primitive));
    }
  }

  if (map != nullptr) *map = std::move(parsed);
  return true;
}

bool LoadMapJsonFile(const std::string& path, MapData* map, std::string* error) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    *error = "cannot open map JSON: " + path;
    return false;
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return ParseMapJson(buffer.str(), map, error);
}

bool ParseRouteJson(const std::string& text, RouteData* route,
                    std::string* error) {
  if (route == nullptr || error == nullptr) return false;
  JsonValue root;
  JsonParser parser(text);
  if (!parser.Parse(&root, error)) return false;
  if (!RequireObject(root, "route", error)) return false;

  RouteData parsed;
  if (!RequireStringField(root, "map", "route.map", &parsed.map_name, error)) {
    return false;
  }
  const JsonValue* waypoints = root.Find("waypoints");
  if (waypoints == nullptr) {
    *error = "route.waypoints: missing";
    return false;
  }
  if (!RequireArray(*waypoints, "route.waypoints", error)) return false;
  parsed.corridor_points = static_cast<std::int64_t>(waypoints->array.size());

  std::vector<Point> points;
  std::vector<int> road_ids;
  points.reserve(waypoints->array.size());
  road_ids.reserve(waypoints->array.size());
  for (std::size_t index = 0; index < waypoints->array.size(); ++index) {
    const JsonValue& row = waypoints->array[index];
    const std::string path = "route.waypoints[" + std::to_string(index) + "]";
    if (!RequireArray(row, path, error)) return false;
    if (row.array.size() != 4) {
      *error = path + ": expected [x, y, heading_rad, road_id]";
      return false;
    }
    Point point{};
    double heading = 0.0;
    double road_id = 0.0;
    if (!RequireNumber(row.array[0], path + "[0]", &point.x, error) ||
        !RequireNumber(row.array[1], path + "[1]", &point.y, error) ||
        !RequireNumber(row.array[2], path + "[2]", &heading, error) ||
        !RequireNumber(row.array[3], path + "[3]", &road_id, error)) {
      return false;
    }
    points.push_back(point);
    road_ids.push_back(static_cast<int>(std::llround(road_id)));
  }

  // One run of constant road id per line.  `centerlines` keeps each run of two
  // or more waypoints as it is (the points ICD A16 counts).  `corridor_lines`,
  // which _pack_route draws, starts each run after the first at the previous
  // run's last waypoint, so the corridor has no break where the road changes;
  // a run of one waypoint therefore still makes a line.
  std::size_t start = 0;
  for (std::size_t index = 1; index <= points.size(); ++index) {
    const bool boundary =
        index == points.size() || road_ids[index] != road_ids[start];
    if (!boundary) continue;
    if (index - start >= 2) {
      parsed.centerlines.emplace_back(points.begin() +
                                          static_cast<std::ptrdiff_t>(start),
                                      points.begin() +
                                          static_cast<std::ptrdiff_t>(index));
    }
    const std::size_t first = start == 0 ? 0 : start - 1;
    if (index - first >= 2) {
      parsed.corridor_lines.emplace_back(
          points.begin() + static_cast<std::ptrdiff_t>(first),
          points.begin() + static_cast<std::ptrdiff_t>(index));
    }
    start = index;
  }

  const JsonValue* destination = root.Find("destination");
  if (destination == nullptr) {
    *error = "route.destination: missing";
    return false;
  }
  if (!RequireArray(*destination, "route.destination", error)) return false;
  if (destination->array.size() != 2) {
    *error = "route.destination: expected [x, y]";
    return false;
  }
  if (!RequireNumber(destination->array[0], "route.destination[0]",
                     &parsed.destination.x, error) ||
      !RequireNumber(destination->array[1], "route.destination[1]",
                     &parsed.destination.y, error)) {
    return false;
  }
  parsed.destination_valid = true;
  parsed.valid = parsed.corridor_points >= 2 && !parsed.corridor_lines.empty();
  parsed.sha256 = Sha256Hex(text);
  *route = std::move(parsed);
  return true;
}

bool LoadRouteJsonFile(const std::string& path, RouteData* route,
                       std::string* error) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    *error = "cannot open route file: " + path;
    return false;
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return ParseRouteJson(buffer.str(), route, error);
}

// --------------------------------------------------------------- rasterizer

namespace {

// The map channels are filled by a span rasterizer that reproduces upstream's
// per-pixel decisions bit for bit: the same coordinate expressions, the same
// threshold comparisons and the same writes as
// `navigation_rasterizer.cpp`; only the loop order and the early exits differ.
// The output zeroing and the whole route overlay stay in upstream's own
// renderer (called with no map primitives), so they are exact by construction.

constexpr std::int32_t kDirectionSinChannel = 7;
constexpr std::int32_t kDirectionCosChannel = 8;
constexpr std::int32_t kDirectionValidChannel = 9;
constexpr std::int32_t kRoadLevelChannel = 11;
constexpr std::int32_t kRoadLevelValidChannel = 12;
constexpr std::int32_t kLevelAmbiguityChannel = 13;

// Map-frame slack added to the raster window for culling.  A primitive can only
// write pixels inside its point bounding box inflated by its own draw reach
// (see RepackMap/PackRoute), so one metre on the window side is ample.
constexpr double kCullMarginM = 1.0;

struct PrimitiveStyle {
  std::int32_t channel = 0;
  std::int32_t level = 0;
  bool level_valid = false;
  float width_m = 0.0F;
  float value = 1.0F;
};

// pixel_center() of the native renderer, one axis at a time.
inline double PixelX(std::int32_t row) {
  return kXMaxM - (static_cast<double>(row) + 0.5) * kMetersPerPixel;
}

inline double PixelY(std::int32_t column) {
  return kYMaxM - (static_cast<double>(column) + 0.5) * kMetersPerPixel;
}

// pixel_bounds() of the native renderer with an explicit padding in pixels.
// The clamp before the cast keeps the double->int conversion defined; in the
// range the renderer can see it is a no-op.  The caller may pass less padding
// than the native renderer (its +1 px of slack); the candidate set only has to
// contain every pixel that can be written, the exact tests then decide.
std::array<std::int32_t, 4> PixelBoundsPx(const Point* points, std::size_t count,
                                          double padding_px) {
  double min_row = std::numeric_limits<double>::infinity();
  double max_row = -std::numeric_limits<double>::infinity();
  double min_column = std::numeric_limits<double>::infinity();
  double max_column = -std::numeric_limits<double>::infinity();
  for (std::size_t index = 0; index < count; ++index) {
    const double pixel_x = (kXMaxM - points[index].x) / kMetersPerPixel - 0.5;
    const double pixel_y = (kYMaxM - points[index].y) / kMetersPerPixel - 0.5;
    min_row = std::min(min_row, pixel_x - padding_px);
    max_row = std::max(max_row, pixel_x + padding_px);
    min_column = std::min(min_column, pixel_y - padding_px);
    max_column = std::max(max_column, pixel_y + padding_px);
  }
  const double kCastLimit = 1.0e6;
  return {
      std::max<std::int32_t>(
          0, static_cast<std::int32_t>(std::floor(
                 std::clamp(min_row, -kCastLimit, kCastLimit)))),
      std::min<std::int32_t>(
          kHeightPx - 1, static_cast<std::int32_t>(std::ceil(
                             std::clamp(max_row, -kCastLimit, kCastLimit)))),
      std::max<std::int32_t>(
          0, static_cast<std::int32_t>(std::floor(
                 std::clamp(min_column, -kCastLimit, kCastLimit)))),
      std::min<std::int32_t>(
          kWidthPx - 1, static_cast<std::int32_t>(std::ceil(
                            std::clamp(max_column, -kCastLimit, kCastLimit)))),
  };
}

// The native renderer's own bounds: padding_m plus one pixel.
std::array<std::int32_t, 4> PixelBounds(const Point* points, std::size_t count,
                                        double padding_m) {
  return PixelBoundsPx(points, count, padding_m / kMetersPerPixel + 1.0);
}

float EncodeLevel(std::int32_t level) {
  const float clamped = std::clamp(static_cast<float>(level), -8.0F, 8.0F);
  return (clamped + 8.0F) / 16.0F;
}

std::int32_t DecodeLevel(float value) {
  return static_cast<std::int32_t>(std::lround(value * 16.0F - 8.0F));
}

// Base pointer of every map channel, so a pixel write needs no channel
// arithmetic in the raster loops.
using ChannelBases = std::array<float*, kMapChannels>;

ChannelBases MapChannelBases(float* map_output) {
  ChannelBases bases{};
  const std::size_t channel_size =
      static_cast<std::size_t>(kHeightPx) * kWidthPx;
  for (std::int32_t channel = 0; channel < kMapChannels; ++channel) {
    bases[static_cast<std::size_t>(channel)] =
        map_output + static_cast<std::size_t>(channel) * channel_size;
  }
  return bases;
}

inline float* RowPointer(float* channel_base, std::int32_t row) {
  return channel_base + static_cast<std::size_t>(row) * kWidthPx;
}

// apply_level() of the native renderer.  This library always renders with no
// active level filter (`active_level_valid` is 0 at every nav_render call), so
// upstream's active-level branch is unreachable and not carried over.
bool ApplyLevel(std::int32_t row, std::int32_t column,
                const PrimitiveStyle& style, const ChannelBases& bases) {
  if (!style.level_valid) return true;
  float* const valid_row = RowPointer(bases[kRoadLevelValidChannel], row);
  float* const level_row = RowPointer(bases[kRoadLevelChannel], row);
  float* const ambiguity_row = RowPointer(bases[kLevelAmbiguityChannel], row);
  if (valid_row[column] > 0.5F &&
      DecodeLevel(level_row[column]) != style.level) {
    ambiguity_row[column] = 1.0F;
  }
  level_row[column] = EncodeLevel(style.level);
  valid_row[column] = 1.0F;
  return true;
}

// The channel base of a primitive, or null when the channel is outside the map
// raster (upstream's write_semantic_pixel then writes nothing at all).
inline float* SemanticChannel(const PrimitiveStyle& style,
                              const ChannelBases& bases) {
  if (style.channel < 0 || style.channel >= kMapChannels) return nullptr;
  return bases[static_cast<std::size_t>(style.channel)];
}

void WriteSemanticPixel(std::int32_t row, std::int32_t column,
                        const PrimitiveStyle& style, float* channel_base,
                        const ChannelBases& bases) {
  if (channel_base == nullptr) return;
  if (!ApplyLevel(row, column, style, bases)) return;
  RowPointer(channel_base, row)[column] = style.value;
}

// First row of [row_begin, row_end] whose pixel centre is left of the crossing,
// or row_end + 1 when there is none.  Pixel x strictly decreases with the row,
// so the predicate is monotone and the estimate only has to land near the
// boundary; the two loops then settle it against the exact comparison.
std::int32_t FirstRowBelow(double x_intersection, std::int32_t row_begin,
                           std::int32_t row_end) {
  const double estimate = (kXMaxM - x_intersection) / kMetersPerPixel - 0.5;
  std::int32_t row = row_begin;
  if (estimate > static_cast<double>(row_end) + 1.0) {
    row = row_end + 1;
  } else if (estimate > static_cast<double>(row_begin)) {
    row = static_cast<std::int32_t>(std::floor(estimate));
  }
  while (row > row_begin && PixelX(row - 1) < x_intersection) --row;
  while (row <= row_end && !(PixelX(row) < x_intersection)) ++row;
  return row;
}

// draw_polygon() as spans.  point_in_polygon toggles once per crossed edge, so
// a pixel centre is inside exactly when an odd number of crossings has been
// passed: with the crossing rows sorted, the spans start at the first crossing
// and alternate.  Per-pixel decisions and writes are unchanged; the polygon is
// scanned column by column because the crossing test uses the column
// coordinate, exactly as the native renderer does.
void FillPolygon(const Point* points, std::size_t count,
                 const PrimitiveStyle& style, const ChannelBases& bases,
                 std::vector<std::int32_t>* crossings) {
  const auto bounds = PixelBounds(points, count, 0.0);
  if (bounds[0] > bounds[1] || bounds[2] > bounds[3]) return;
  float* const channel_base = SemanticChannel(style, bases);
  const std::int32_t row_begin = bounds[0];
  const std::int32_t row_end = bounds[1];
  for (std::int32_t column = bounds[2]; column <= bounds[3]; ++column) {
    const double pixel_y = PixelY(column);
    crossings->clear();
    std::size_t previous = count - 1;
    for (std::size_t current = 0; current < count; previous = current++) {
      const Point& a = points[current];
      const Point& b = points[previous];
      if ((a.y > pixel_y) == (b.y > pixel_y)) continue;
      const double x_intersection =
          (b.x - a.x) * (pixel_y - a.y) / (b.y - a.y) + a.x;
      const std::int32_t first_row =
          FirstRowBelow(x_intersection, row_begin, row_end);
      if (first_row > row_end) continue;
      crossings->insert(
          std::lower_bound(crossings->begin(), crossings->end(), first_row),
          first_row);
    }
    for (std::size_t index = 0; index < crossings->size(); index += 2) {
      const std::int32_t begin = (*crossings)[index];
      const std::int32_t end =
          index + 1 < crossings->size()
              ? std::min(row_end, (*crossings)[index + 1] - 1)
              : row_end;
      if (channel_base != nullptr && !style.level_valid) {
        // constant value, no level side effects: the row range is a fill
        for (std::int32_t row = begin; row <= end; ++row) {
          RowPointer(channel_base, row)[column] = style.value;
        }
      } else {
        for (std::int32_t row = begin; row <= end; ++row) {
          WriteSemanticPixel(row, column, style, channel_base, bases);
        }
      }
    }
  }
}

// Slack in pixels on top of the stroke radius for the candidate box: the box
// only has to contain every pixel centre within the radius of the geometry, and
// the exact test then decides each candidate.
constexpr double kCandidateSlackPx = 1.0e-6;

// A pixel is drawn when the native renderer's point_segment_distance() does not
// exceed half_width.  Comparing the squared distance instead skips the libm
// hypot for all but a razor-thin band around the threshold: only there (a
// nanometre in distance) can the two comparisons disagree, and the band falls
// back to the exact expression, so the decision is upstream's.
constexpr double kDistanceBandM = 1.0e-6;

inline bool DistanceAtMost(double squared, double delta_x, double delta_y,
                           double limit) {
  const double inner = limit - kDistanceBandM;
  if (squared <= inner * inner) return true;
  const double outer = limit + kDistanceBandM;
  if (squared > outer * outer) return false;
  return std::hypot(delta_x, delta_y) <= limit;
}

// Same predicate for a whole segment, without the per-pixel division: for a
// pixel projecting inside the segment, distance^2 = (|w|^2 * |d|^2 - (w.d)^2) /
// |d|^2, so the comparison is carried out scaled by |d|^2.  Pixels projecting
// before the start or past the end use the endpoint distance.  Inside the band
// around the threshold the native renderer's own arithmetic is evaluated, from
// the very same expressions, so the decision is its decision.
inline bool SegmentWithinWidth(const Point& start, double end_x, double end_y,
                               double pixel_x, double pixel_y, double delta_x,
                               double delta_y, double projection,
                               double squared_norm, double dx, double dy,
                               double length_squared, double half_width) {
  if (projection <= 0.0) {
    return DistanceAtMost(squared_norm, delta_x, delta_y, half_width);
  }
  if (projection >= length_squared) {
    // nearest point is start + 1.0 * d, the value upstream computes
    const double end_delta_x = pixel_x - end_x;
    const double end_delta_y = pixel_y - end_y;
    return DistanceAtMost(end_delta_x * end_delta_x + end_delta_y * end_delta_y,
                          end_delta_x, end_delta_y, half_width);
  }
  const double inner = half_width - kDistanceBandM;
  const double outer = half_width + kDistanceBandM;
  const double scaled = squared_norm * length_squared - projection * projection;
  if (scaled <= inner * inner * length_squared) return true;
  if (scaled > outer * outer * length_squared) return false;
  const double fraction = projection / length_squared;
  return std::hypot(pixel_x - (start.x + fraction * dx),
                    pixel_y - (start.y + fraction * dy)) <= half_width;
}

// draw_line(): every segment in order, so overlapping segments of a direction
// line still overwrite each other in the upstream order.  The segment direction
// is only computed for direction lines (upstream computes it unconditionally,
// which has no effect on the output).
template <bool kDirection>
void DrawLine(const Point* points, std::size_t count,
              const PrimitiveStyle& style, const ChannelBases& bases) {
  const double half_width =
      std::max(style.width_m * 0.5F,
               static_cast<float>(kMetersPerPixel * 0.5));
  float* const channel_base = SemanticChannel(style, bases);
  for (std::size_t segment = 0; segment + 1 < count; ++segment) {
    const Point start = points[segment];
    const Point end = points[segment + 1];
    const Point segment_points[2] = {start, end};
    const auto bounds = PixelBoundsPx(
        segment_points, 2, half_width / kMetersPerPixel + kCandidateSlackPx);
    if (bounds[0] > bounds[1] || bounds[2] > bounds[3]) continue;
    float direction_sin = 0.0F;
    float direction_cos = 0.0F;
    if (kDirection) {
      const double theta = std::atan2(end.y - start.y, end.x - start.x);
      direction_sin = static_cast<float>((std::sin(theta) + 1.0) * 0.5);
      direction_cos = static_cast<float>((std::cos(theta) + 1.0) * 0.5);
    }
    const double dx = end.x - start.x;
    const double dy = end.y - start.y;
    const double length_squared = dx * dx + dy * dy;
    const bool degenerate = length_squared <= 1e-12;
    // upstream's nearest point for a clamped fraction of 1
    const double end_projection_x = start.x + dx;
    const double end_projection_y = start.y + dy;
    for (std::int32_t row = bounds[0]; row <= bounds[1]; ++row) {
      const double pixel_x = PixelX(row);
      const double row_delta_x = pixel_x - start.x;
      const double row_projection = row_delta_x * dx;
      const double row_squared = row_delta_x * row_delta_x;
      float* const sin_row =
          kDirection ? RowPointer(bases[kDirectionSinChannel], row) : nullptr;
      float* const cos_row =
          kDirection ? RowPointer(bases[kDirectionCosChannel], row) : nullptr;
      float* const valid_row =
          kDirection ? RowPointer(bases[kDirectionValidChannel], row) : nullptr;
      for (std::int32_t column = bounds[2]; column <= bounds[3]; ++column) {
        const double pixel_y = PixelY(column);
        const double delta_y = pixel_y - start.y;
        const double projection = row_projection + delta_y * dy;
        const double squared_norm = row_squared + delta_y * delta_y;
        const bool inside =
            degenerate
                ? DistanceAtMost(squared_norm, row_delta_x, delta_y, half_width)
                : SegmentWithinWidth(start, end_projection_x, end_projection_y,
                                     pixel_x, pixel_y, row_delta_x, delta_y,
                                     projection, squared_norm, dx, dy,
                                     length_squared, half_width);
        if (!inside) continue;
        if (kDirection) {
          if (!ApplyLevel(row, column, style, bases)) continue;
          sin_row[column] = direction_sin;
          cos_row[column] = direction_cos;
          valid_row[column] = 1.0F;
        } else {
          WriteSemanticPixel(row, column, style, channel_base, bases);
        }
      }
    }
  }
}

// draw_point(): one disc of radius max(width/2, half a pixel).
void DrawPoint(const Point& point, const PrimitiveStyle& style,
               const ChannelBases& bases) {
  const double radius =
      std::max(style.width_m * 0.5F,
               static_cast<float>(kMetersPerPixel * 0.5));
  const auto bounds =
      PixelBoundsPx(&point, 1, radius / kMetersPerPixel + kCandidateSlackPx);
  if (bounds[0] > bounds[1] || bounds[2] > bounds[3]) return;
  float* const channel_base = SemanticChannel(style, bases);
  for (std::int32_t row = bounds[0]; row <= bounds[1]; ++row) {
    const double pixel_x = PixelX(row);
    for (std::int32_t column = bounds[2]; column <= bounds[3]; ++column) {
      const double pixel_y = PixelY(column);
      const double delta_x = pixel_x - point.x;
      const double delta_y = pixel_y - point.y;
      if (DistanceAtMost(delta_x * delta_x + delta_y * delta_y, delta_x,
                         delta_y, radius)) {
        WriteSemanticPixel(row, column, style, channel_base, bases);
      }
    }
  }
}

// Map-frame bounding box of the raster window of one pose: the four corners of
// the ego-frame geometry rectangle, rotated into the map frame (ego_to_map of
// the native renderer), inflated by the culling margin.
std::array<double, 4> WindowBounds(double x_map_m, double y_map_m,
                                   double cosine, double sine) {
  double min_x = std::numeric_limits<double>::infinity();
  double min_y = std::numeric_limits<double>::infinity();
  double max_x = -std::numeric_limits<double>::infinity();
  double max_y = -std::numeric_limits<double>::infinity();
  for (const double ego_x : {kXMinM - kCullMarginM, kXMaxM + kCullMarginM}) {
    for (const double ego_y : {kYMinM - kCullMarginM, kYMaxM + kCullMarginM}) {
      const double map_x = x_map_m + cosine * ego_x - sine * ego_y;
      const double map_y = y_map_m + sine * ego_x + cosine * ego_y;
      min_x = std::min(min_x, map_x);
      max_x = std::max(max_x, map_x);
      min_y = std::min(min_y, map_y);
      max_y = std::max(max_y, map_y);
    }
  }
  return {min_x, min_y, max_x, max_y};
}

inline bool BoxesIntersect(const std::array<double, 4>& a,
                           const std::array<double, 4>& b) {
  return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
}

}  // namespace

const char* NavigationRasterizer::RendererVersion() {
  return nav_renderer_version();
}

bool NavigationRasterizer::LoadMap(const std::string& path, std::string* error) {
  MapData map;
  if (!LoadMapJsonFile(path, &map, error)) return false;
  SetMap(std::move(map));
  return true;
}

bool NavigationRasterizer::LoadRoute(const std::string& path,
                                     std::string* error) {
  RouteData route;
  if (!LoadRouteJsonFile(path, &route, error)) return false;
  SetRoute(std::move(route));
  return true;
}

void NavigationRasterizer::SetMap(MapData map) {
  map_ = std::move(map);
  has_map_ = true;
  RepackMap();
  RefreshEffectiveRoute();
}

void NavigationRasterizer::SetRoute(RouteData route) {
  route_ = std::move(route);
  has_route_ = true;
  PackRoute();
  RefreshEffectiveRoute();
}

void NavigationRasterizer::RefreshEffectiveRoute() {
  packed_route_usable_ = EffectiveRouteValid();
}

// _pack_primitives, once per map: the same interleaved doubles and the same
// fields in the same order as the reference path, plus the inflated map-frame
// bounding box each primitive can touch.
void NavigationRasterizer::RepackMap() {
  map_points_.clear();
  packed_map_.clear();
  std::size_t point_total = 0;
  for (const Primitive& primitive : map_.primitives) {
    point_total += primitive.points.size();
  }
  map_points_.reserve(point_total * 2);
  packed_map_.reserve(map_.primitives.size());
  for (const Primitive& primitive : map_.primitives) {
    PackedMapPrimitive packed;
    packed.point_offset = static_cast<std::int32_t>(map_points_.size() / 2);
    packed.point_count = static_cast<std::int32_t>(primitive.points.size());
    packed.kind = static_cast<std::int32_t>(primitive.kind);
    packed.channel = primitive.channel;
    packed.level = primitive.level_valid ? primitive.level : 0;
    packed.level_valid = primitive.level_valid ? 1 : 0;
    packed.width_m = primitive.width_m;
    packed.value = primitive.value;
    double min_x = std::numeric_limits<double>::infinity();
    double min_y = std::numeric_limits<double>::infinity();
    double max_x = -std::numeric_limits<double>::infinity();
    double max_y = -std::numeric_limits<double>::infinity();
    for (const Point& point : primitive.points) {
      map_points_.push_back(point.x);
      map_points_.push_back(point.y);
      min_x = std::min(min_x, point.x);
      max_x = std::max(max_x, point.x);
      min_y = std::min(min_y, point.y);
      max_y = std::max(max_y, point.y);
    }
    double reach = kCullMarginM;
    switch (primitive.kind) {
      case PrimitiveKind::kLine:
      case PrimitiveKind::kDirectionLine:
      case PrimitiveKind::kPoint:
        // furthest pixel centre a drawn stroke can reach from its geometry
        reach += std::max(0.5 * static_cast<double>(primitive.width_m),
                          0.5 * kMetersPerPixel);
        break;
      case PrimitiveKind::kPolygon:
        break;  // only pixels inside the polygon are written
    }
    packed.bounds = {min_x - reach, min_y - reach, max_x + reach,
                     max_y + reach};
    packed_map_.push_back(packed);
  }
}

// _pack_route, once per route: one contiguous run of points per corridor line,
// the offsets the native renderer takes, and the per-line culling boxes.
void NavigationRasterizer::PackRoute() {
  route_points_.clear();
  route_offsets_.clear();
  packed_route_lines_.clear();
  route_offsets_.push_back(0);
  route_destination_ = {{0.0, 0.0}};
  std::size_t point_total = 0;
  for (const std::vector<Point>& line : route_.corridor_lines) {
    point_total += line.size();
  }
  route_points_.reserve(point_total * 2);
  packed_route_lines_.reserve(route_.corridor_lines.size());
  const double reach = 0.5 * static_cast<double>(kRouteCorridorWidthM) +
                       kCullMarginM;
  for (const std::vector<Point>& line : route_.corridor_lines) {
    PackedRouteLine packed;
    packed.point_offset = static_cast<std::int32_t>(route_points_.size() / 2);
    packed.point_count = static_cast<std::int32_t>(line.size());
    double min_x = std::numeric_limits<double>::infinity();
    double min_y = std::numeric_limits<double>::infinity();
    double max_x = -std::numeric_limits<double>::infinity();
    double max_y = -std::numeric_limits<double>::infinity();
    for (const Point& point : line) {
      route_points_.push_back(point.x);
      route_points_.push_back(point.y);
      min_x = std::min(min_x, point.x);
      max_x = std::max(max_x, point.x);
      min_y = std::min(min_y, point.y);
      max_y = std::max(max_y, point.y);
    }
    packed.bounds = {min_x - reach, min_y - reach, max_x + reach,
                     max_y + reach};
    packed_route_lines_.push_back(packed);
    route_offsets_.push_back(
        static_cast<std::int32_t>(route_points_.size() / 2));
  }
  if (route_.destination_valid) {
    route_destination_ = {{route_.destination.x, route_.destination.y}};
  }
}

bool NavigationRasterizer::Render(double x_map_m, double y_map_m,
                                  double yaw_map_rad,
                                  std::vector<float>* map_context,
                                  std::vector<std::uint8_t>* route_mask,
                                  std::string* error) const {
  if (map_context == nullptr || route_mask == nullptr) {
    if (error) *error = "Render: null output buffer";
    return false;
  }
  // The buffers are only sized here: every byte is written below (zeroing by
  // the native renderer), so nothing is zero-filled twice.
  if (map_context->size() != MapContextSize()) {
    map_context->resize(MapContextSize());
  }
  if (route_mask->size() != RouteMaskSize()) {
    route_mask->resize(RouteMaskSize());
  }
  const double cosine = std::cos(yaw_map_rad);
  const double sine = std::sin(yaw_map_rad);
  const std::array<double, 4> window =
      WindowBounds(x_map_m, y_map_m, cosine, sine);

  // Route corridor: cull the corridor lines whose box misses the window, keeping
  // upstream order and point sequence.
  render_route_points_.clear();
  render_route_offsets_.clear();
  render_route_offsets_.push_back(0);
  if (packed_route_usable_) {
    for (const PackedRouteLine& line : packed_route_lines_) {
      if (!BoxesIntersect(line.bounds, window)) continue;
      const std::size_t first =
          static_cast<std::size_t>(line.point_offset) * 2;
      render_route_points_.insert(
          render_route_points_.end(), route_points_.begin() + first,
          route_points_.begin() + first +
              static_cast<std::size_t>(line.point_count) * 2);
      render_route_offsets_.push_back(
          static_cast<std::int32_t>(render_route_points_.size() / 2));
    }
  }
  const std::int32_t route_line_count =
      static_cast<std::int32_t>(render_route_offsets_.size()) - 1;

  // Destination: only skipped when it is clearly outside the window; upstream's
  // own bounds test then decides whether anything is drawn.
  bool destination_valid = false;
  if (packed_route_usable_) {
    const double dx = route_destination_[0] - x_map_m;
    const double dy = route_destination_[1] - y_map_m;
    const double ego_x = cosine * dx + sine * dy;
    const double ego_y = -sine * dx + cosine * dy;
    destination_valid = ego_x >= kXMinM - kCullMarginM &&
                        ego_x <= kXMaxM + kCullMarginM &&
                        ego_y >= kYMinM - kCullMarginM &&
                        ego_y <= kYMaxM + kCullMarginM;
  }

  // Zero both rasters and draw the route with upstream's own renderer: no map
  // primitive is passed, so only the memset and the corridor/destination
  // writes happen there.
  NavPose pose{};
  pose.x_enu_m = x_map_m;
  pose.y_enu_m = y_map_m;
  pose.yaw_rad = yaw_map_rad;
  NavGeometry geometry{};
  geometry.height_px = kHeightPx;
  geometry.width_px = kWidthPx;
  geometry.meters_per_pixel = kMetersPerPixel;
  geometry.x_min_m = kXMinM;
  geometry.x_max_m = kXMaxM;
  geometry.y_min_m = kYMinM;
  geometry.y_max_m = kYMaxM;
  const std::int32_t status = nav_render(
      nullptr, 0, nullptr, 0,
      render_route_points_.empty() ? nullptr : render_route_points_.data(),
      static_cast<std::int32_t>(render_route_points_.size() / 2),
      render_route_offsets_.data(), route_line_count, route_destination_.data(),
      destination_valid ? 1 : 0, pose, geometry, kRouteCorridorWidthM,
      kDestinationMarkerRadiusM, kRouteRearClipM, 0, 0, map_context->data(),
      route_mask->data());
  if (status != 0) {
    if (error) {
      *error = "upstream nav_render failed: status=" + std::to_string(status);
    }
    return false;
  }

  // Map channels: the culled primitives in upstream's packing order, which is
  // the draw order the overlapping writes depend on.
  render_selection_.clear();
  for (std::size_t index = 0; index < packed_map_.size(); ++index) {
    if (BoxesIntersect(packed_map_[index].bounds, window)) {
      render_selection_.push_back(static_cast<std::int32_t>(index));
    }
  }
  const ChannelBases bases = MapChannelBases(map_context->data());
  for (const std::int32_t index : render_selection_) {
    const PackedMapPrimitive& primitive = packed_map_[index];
    render_ego_points_.clear();
    const std::size_t first = static_cast<std::size_t>(primitive.point_offset);
    for (std::int32_t point = 0; point < primitive.point_count; ++point) {
      const double dx = map_points_[2 * (first + point)] - x_map_m;
      const double dy = map_points_[2 * (first + point) + 1] - y_map_m;
      render_ego_points_.push_back({cosine * dx + sine * dy,
                                    -sine * dx + cosine * dy});
    }
    PrimitiveStyle style;
    style.channel = primitive.channel;
    style.level = primitive.level;
    style.level_valid = primitive.level_valid != 0;
    style.width_m = primitive.width_m;
    style.value = primitive.value;
    const Point* points = render_ego_points_.data();
    const std::size_t count = render_ego_points_.size();
    switch (primitive.kind) {
      case static_cast<std::int32_t>(PrimitiveKind::kLine):
        if (count >= 2) DrawLine<false>(points, count, style, bases);
        break;
      case static_cast<std::int32_t>(PrimitiveKind::kPolygon):
        if (count >= 3) {
          FillPolygon(points, count, style, bases, &render_crossings_);
        }
        break;
      case static_cast<std::int32_t>(PrimitiveKind::kPoint):
        if (count >= 1) DrawPoint(points[0], style, bases);
        break;
      case static_cast<std::int32_t>(PrimitiveKind::kDirectionLine):
        if (count >= 2) DrawLine<true>(points, count, style, bases);
        break;
      default:
        if (error) {
          *error = "Render: unsupported primitive kind " +
                   std::to_string(primitive.kind);
        }
        return false;
    }
  }
  return true;
}

bool NavigationRasterizer::RenderReference(double x_map_m, double y_map_m,
                                           double yaw_map_rad,
                                           std::vector<float>* map_context,
                                           std::vector<std::uint8_t>* route_mask,
                                           std::string* error) const {
  if (map_context == nullptr || route_mask == nullptr) {
    if (error) *error = "Render: null output buffer";
    return false;
  }
  map_context->assign(MapContextSize(), 0.0F);
  route_mask->assign(RouteMaskSize(), 0);

  // _pack_primitives: interleaved doubles, one NavPrimitive per spec.
  std::vector<double> map_points;
  std::vector<NavPrimitive> primitives;
  primitives.reserve(map_.primitives.size());
  for (const Primitive& primitive : map_.primitives) {
    NavPrimitive packed{};
    packed.point_offset = static_cast<std::int32_t>(map_points.size() / 2);
    packed.point_count = static_cast<std::int32_t>(primitive.points.size());
    packed.kind = static_cast<std::int32_t>(primitive.kind);
    packed.channel = primitive.channel;
    packed.level = primitive.level_valid ? primitive.level : 0;
    packed.level_valid = primitive.level_valid ? 1 : 0;
    packed.width_m = primitive.width_m;
    packed.value = primitive.value;
    for (const Point& point : primitive.points) {
      map_points.push_back(point.x);
      map_points.push_back(point.y);
    }
    primitives.push_back(packed);
  }

  // _pack_route.  An invalid route or a route of another map renders zeros,
  // the way upstream's render() falls back to an empty route.
  const bool route_valid = EffectiveRouteValid();
  std::vector<double> route_points;
  std::vector<std::int32_t> route_offsets{0};
  std::array<double, 2> destination{{0.0, 0.0}};
  std::int32_t route_line_count = 0;
  if (route_valid) {
    for (const std::vector<Point>& line : route_.corridor_lines) {
      for (const Point& point : line) {
        route_points.push_back(point.x);
        route_points.push_back(point.y);
      }
      route_offsets.push_back(
          static_cast<std::int32_t>(route_points.size() / 2));
    }
    route_line_count = static_cast<std::int32_t>(route_offsets.size()) - 1;
    destination = {{route_.destination.x, route_.destination.y}};
  }

  NavPose pose{};
  pose.x_enu_m = x_map_m;
  pose.y_enu_m = y_map_m;
  pose.yaw_rad = yaw_map_rad;
  NavGeometry geometry{};
  geometry.height_px = kHeightPx;
  geometry.width_px = kWidthPx;
  geometry.meters_per_pixel = kMetersPerPixel;
  geometry.x_min_m = kXMinM;
  geometry.x_max_m = kXMaxM;
  geometry.y_min_m = kYMinM;
  geometry.y_max_m = kYMaxM;

  const std::int32_t status = nav_render(
      map_points.empty() ? nullptr : map_points.data(),
      static_cast<std::int32_t>(map_points.size() / 2),
      primitives.empty() ? nullptr : primitives.data(),
      static_cast<std::int32_t>(primitives.size()),
      route_points.empty() ? nullptr : route_points.data(),
      static_cast<std::int32_t>(route_points.size() / 2), route_offsets.data(),
      route_line_count, destination.data(), route_valid ? 1 : 0, pose, geometry,
      kRouteCorridorWidthM, kDestinationMarkerRadiusM, kRouteRearClipM, 0, 0,
      map_context->data(), route_mask->data());
  if (status != 0) {
    if (error) {
      *error = "upstream nav_render failed: status=" + std::to_string(status);
    }
    return false;
  }
  return true;
}

RouteValidity NavigationRasterizer::EvaluateRoute(
    const RouteAnnouncement* announcement, double now_simulation_s,
    const std::vector<std::uint8_t>& route_mask) const {
  RouteValidity validity;
  const std::size_t corridor_channel =
      static_cast<std::size_t>(RouteChannel::kSelectedCorridor) * kHeightPx *
      kWidthPx;
  bool corridor_pixel = false;
  if (route_mask.size() >= RouteMaskSize()) {
    for (std::size_t index = 0; index < static_cast<std::size_t>(kHeightPx) *
                                                  static_cast<std::size_t>(kWidthPx);
         ++index) {
      if (route_mask[corridor_channel + index] != 0) {
        corridor_pixel = true;
        break;
      }
    }
  }
  validity.corridor_present = corridor_pixel;
  validity.has_announcement = announcement != nullptr;
  validity.corridor_declared =
      announcement != nullptr && announcement->corridorPoints > 0;
  validity.empty = !corridor_pixel ||
                   (announcement != nullptr && announcement->corridorPoints == 0);
  if (announcement != nullptr) {
    validity.route_age_seconds = now_simulation_s - announcement->issueTime;
    validity.stale = validity.route_age_seconds > kRouteStaleSeconds;
  } else {
    validity.route_age_seconds =
        std::numeric_limits<double>::infinity();
    validity.stale = true;  // nothing announced yet: nothing to trust
  }
  // An empty corridor is reported first: it is a definite condition, while a
  // stale route may merely be late.  Both set the stop response (REQ-025).
  validity.cause = validity.empty
                       ? kCauseRouteEmpty
                       : (validity.stale ? kCauseRouteStale : kCauseNone);
  return validity;
}

}  // namespace de4sdv::driving::navigation
