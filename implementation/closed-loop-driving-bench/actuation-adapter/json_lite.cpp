#include "json_lite.h"

#include <cerrno>
#include <cstdlib>
#include <cstring>

namespace de4sdv::driving::json {
namespace {

constexpr int kMaxDepth = 64;

}  // namespace
const Value* Value::Find(const std::string& key) const {
  if (type_ != Type::kObject) return nullptr;
  for (const auto& member : members_) {
    if (member.first == key) return &member.second;
  }
  return nullptr;
}

const Value* Value::At(std::size_t index) const {
  if (type_ != Type::kArray || index >= items_.size()) return nullptr;
  return &items_[index];
}

class Parser {
 public:
  Parser(const std::string& text, std::string* error) : text_(text), error_(error) {}

  Value ParseDocument() {
    SkipSpace();
    Value value = ParseValue(0);
    if (!failed_) {
      SkipSpace();
      if (pos_ != text_.size()) Fail("trailing characters after the JSON value");
    }
    return failed_ ? Value{} : value;
  }

 private:
  void Fail(const std::string& message) {
    if (!failed_) {
      failed_ = true;
      if (error_ != nullptr) {
        *error_ = message + " at byte " + std::to_string(pos_);
      }
    }
  }

  bool Eof() const { return pos_ >= text_.size(); }
  char Peek() const { return text_[pos_]; }

  void SkipSpace() {
    while (!Eof()) {
      const char c = Peek();
      if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
        ++pos_;
      } else {
        break;
      }
    }
  }

  bool Consume(const char* literal) {
    const std::size_t n = std::strlen(literal);
    if (text_.compare(pos_, n, literal) == 0) {
      pos_ += n;
      return true;
    }
    return false;
  }

  Value ParseValue(int depth) {
    Value value;
    if (depth > kMaxDepth) {
      Fail("nesting deeper than 64");
      return value;
    }
    if (Eof()) {
      Fail("unexpected end of input");
      return value;
    }
    switch (Peek()) {
      case '{': return ParseObject(depth);
      case '[': return ParseArray(depth);
      case '"': {
        std::string s;
        if (!ParseString(&s)) return value;
        value.type_ = Value::Type::kString;
        value.string_ = std::move(s);
        return value;
      }
      case 't':
        if (Consume("true")) {
          value.type_ = Value::Type::kBool;
          value.boolean_ = true;
        } else {
          Fail("invalid literal");
        }
        return value;
      case 'f':
        if (Consume("false")) {
          value.type_ = Value::Type::kBool;
          value.boolean_ = false;
        } else {
          Fail("invalid literal");
        }
        return value;
      case 'n':
        if (Consume("null")) {
          value.type_ = Value::Type::kNull;
        } else {
          Fail("invalid literal");
        }
        return value;
      default: return ParseNumber();
    }
  }

  Value ParseObject(int depth) {
    Value value;
    value.type_ = Value::Type::kObject;
    ++pos_;  // '{'
    SkipSpace();
    if (!Eof() && Peek() == '}') {
      ++pos_;
      return value;
    }
    while (!failed_) {
      SkipSpace();
      if (Eof() || Peek() != '"') {
        Fail("expected a member name");
        return value;
      }
      std::string key;
      if (!ParseString(&key)) return value;
      SkipSpace();
      if (Eof() || Peek() != ':') {
        Fail("expected ':'");
        return value;
      }
      ++pos_;
      SkipSpace();
      Value member = ParseValue(depth + 1);
      if (failed_) return value;
      value.members_.emplace_back(std::move(key), std::move(member));
      SkipSpace();
      if (Eof()) {
        Fail("unterminated object");
        return value;
      }
      if (Peek() == ',') {
        ++pos_;
        continue;
      }
      if (Peek() == '}') {
        ++pos_;
        return value;
      }
      Fail("expected ',' or '}'");
    }
    return value;
  }

  Value ParseArray(int depth) {
    Value value;
    value.type_ = Value::Type::kArray;
    ++pos_;  // '['
    SkipSpace();
    if (!Eof() && Peek() == ']') {
      ++pos_;
      return value;
    }
    while (!failed_) {
      SkipSpace();
      Value item = ParseValue(depth + 1);
      if (failed_) return value;
      value.items_.push_back(std::move(item));
      SkipSpace();
      if (Eof()) {
        Fail("unterminated array");
        return value;
      }
      if (Peek() == ',') {
        ++pos_;
        continue;
      }
      if (Peek() == ']') {
        ++pos_;
        return value;
      }
      Fail("expected ',' or ']'");
    }
    return value;
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
    if (pos_ + 4 > text_.size()) {
      Fail("truncated \\u escape");
      return false;
    }
    std::uint32_t value = 0;
    for (int i = 0; i < 4; ++i) {
      const char c = text_[pos_++];
      value <<= 4;
      if (c >= '0' && c <= '9') {
        value |= static_cast<std::uint32_t>(c - '0');
      } else if (c >= 'a' && c <= 'f') {
        value |= static_cast<std::uint32_t>(c - 'a' + 10);
      } else if (c >= 'A' && c <= 'F') {
        value |= static_cast<std::uint32_t>(c - 'A' + 10);
      } else {
        Fail("invalid hex digit in \\u escape");
        return false;
      }
    }
    *out = value;
    return true;
  }

  bool ParseString(std::string* out) {
    ++pos_;  // '"'
    while (!failed_) {
      if (Eof()) {
        Fail("unterminated string");
        return false;
      }
      const unsigned char c = static_cast<unsigned char>(text_[pos_++]);
      if (c == '"') {
        return true;
      }
      if (c < 0x20) {
        Fail("raw control character in string");
        return false;
      }
      if (c != '\\') {
        out->push_back(static_cast<char>(c));
        continue;
      }
      if (Eof()) {
        Fail("truncated escape");
        return false;
      }
      const char escape = text_[pos_++];
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
          if (code_point >= 0xD800 && code_point <= 0xDBFF) {
            if (pos_ + 2 <= text_.size() && text_[pos_] == '\\' && text_[pos_ + 1] == 'u') {
              pos_ += 2;
              std::uint32_t low = 0;
              if (!ParseHex4(&low)) return false;
              code_point = 0x10000 + ((code_point - 0xD800) << 10) + (low - 0xDC00);
            } else {
              Fail("unpaired high surrogate");
              return false;
            }
          }
          AppendUtf8(code_point, out);
          break;
        }
        default:
          Fail("invalid escape");
          return false;
      }
    }
    return false;
  }

  Value ParseNumber() {
    Value value;
    const std::size_t start = pos_;
    if (!Eof() && Peek() == '-') ++pos_;
    if (Eof() || Peek() < '0' || Peek() > '9') {
      Fail("invalid number");
      return value;
    }
    if (Peek() == '0') {
      ++pos_;
    } else {
      while (!Eof() && Peek() >= '0' && Peek() <= '9') ++pos_;
    }
    if (!Eof() && Peek() == '.') {
      ++pos_;
      if (Eof() || Peek() < '0' || Peek() > '9') {
        Fail("invalid fraction");
        return value;
      }
      while (!Eof() && Peek() >= '0' && Peek() <= '9') ++pos_;
    }
    if (!Eof() && (Peek() == 'e' || Peek() == 'E')) {
      ++pos_;
      if (!Eof() && (Peek() == '+' || Peek() == '-')) ++pos_;
      if (Eof() || Peek() < '0' || Peek() > '9') {
        Fail("invalid exponent");
        return value;
      }
      while (!Eof() && Peek() >= '0' && Peek() <= '9') ++pos_;
    }
    const std::string token = text_.substr(start, pos_ - start);
    errno = 0;
    char* end = nullptr;
    const double parsed = std::strtod(token.c_str(), &end);
    if (end == nullptr || *end != '\0') {
      Fail("invalid number");
      return value;
    }
    value.type_ = Value::Type::kNumber;
    value.number_ = parsed;
    return value;
  }

  const std::string& text_;
  std::string* error_;
  std::size_t pos_ = 0;
  bool failed_ = false;
};

Value Value::Parse(const std::string& text, std::string* error) {
  Parser parser(text, error);
  return parser.ParseDocument();
}

}  // namespace de4sdv::driving::json
