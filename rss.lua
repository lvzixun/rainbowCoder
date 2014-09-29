local lfs = require "lfs"
-- local print_r = require "print_r"

local mt = {}
mt.__index = mt

local function create_stream()
  return setmetatable({}, mt)
end

function mt:write(s, deep)
  deep = deep or 0

  local prefix = ""
  for i=1,deep do
    prefix = prefix.."\t"
  end

  self[#self+1] = prefix..s
end

function mt:dump()
  return table.concat( self, "\n")
end


local function read_file(path)
  local handle = io.open(path, "r")
  local ret = handle:read("*a")
  handle:close()
  return ret
end

local function write_file(path, s)
  local handle = io.open(path, "w")
  handle:write(s)
  handle:close()
end



local function base_name(string_, suffix)
  local LUA_DIRSEP = string.sub(package.config,1,1)
  string_ = string_ or ''
  local basename = string.gsub (string_, '[^'.. LUA_DIRSEP ..']*'.. LUA_DIRSEP ..'', '')
  if suffix then
    basename = string.gsub (basename, suffix, '')
  end
  return basename
end


local function _gen_des(html_file)
  local s = read_file(html_file)
  return string.match(s, ".+<body>(.*)</body>.+")
end

local function _gen_post(path)
  local ret = {}
  for file in lfs.dir(path) do 
    if string.match(file, ".*%.md") and file ~= "index.md" then
      local name = base_name(file, ".md")
      local html_file = path.."/../html/"..name..".html"
      ret[#ret+1] = { 
        link = name..".html", 
        title = name , 
        des = _gen_des(html_file)
      }
    end
  end
  return ret
end


local function _gen_item(stream, deep, item)
  local title = item.title
  local link = item.link
  local des = item.des

  stream:write("<item>", deep)
  stream:write("<title>"..title.."</title>", deep+1)
  stream:write("<link>"..link.."</link>", deep+1)
  stream:write("<description> <![CDATA["..des.."]]></description>", deep+1)
  stream:write("</item>", deep)  
end

local function _gen_rss(items)
  local stream = create_stream()

  -- write header
  stream:write('<?xml version="1.0"?>')
  stream:write('<rss version="2.0">')

    -- write channel
    stream:write("<channel>", 1)
      stream:write("<language>zh-cn</language>", 2)
      stream:write("<copyright>zixun</copyright>", 2)
      stream:write("<generator>www.rainbowcoder.com</generator>", 2)
      stream:write("<title> rainbowcoder </title>", 2)
      stream:write("<link>http://rainbowcoder.com/</link>", 2)
      stream:write("<description> zixun's blog </description>", 2)

      -- write items
      for i=1,#items do
        _gen_item(stream, 2, items[i])
      end
    stream:write("</channel>", 1)
  stream:write("</rss>")

  return stream:dump()
end


local function main(path)
  local items = _gen_post(path)  -- 获取item
  local s = _gen_rss(items)
  write_file("html/rainbowcoder_rss.xml", s)
end


main("post")



