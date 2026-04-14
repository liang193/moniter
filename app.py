import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET

# ================= 配置区 =================
# 你刚刚提供的真实 DeepSeek API Key
API_KEY = "sk-547ca0352aab49b6a75fd75a6f3e43a5"

# DeepSeek 的专属配置
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
# ==========================================

st.set_page_config(page_title="科技前沿 AI 监控", page_icon="🤖", layout="centered")

class WebMonitor:
    def __init__(self):
        self.sources = {
            "机器之心": "https://www.jiqizhixin.com/rss",
            "量子位": "https://www.qbitai.com/feed"
        }

    def get_article_content(self, url):
        """爬取文章全文，供 AI 阅读"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text() for p in paragraphs])
            return content[:2000]
        except Exception as e:
            return ""

    def summarize_with_ai(self, content):
        """调用 DeepSeek 生成一句话摘要"""
        if not content.strip() or not API_KEY:
            return "⚠️ 没抓取到正文内容，AI 无法总结。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "你是一个资深科技编辑。请用极其精炼的1-2句话，总结下面这篇文章的核心内容。直接输出结果，不要废话。"},
                {"role": "user", "content": f"文章内容：\n{content}"}
            ]
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"🤖 DeepSeek 总结失败，可能是额度不足或网络波动: {str(e)}"

    def fetch_articles(self, site_name, days_limit):
        """获取并过滤文章 (增强容错版)"""
        url = self.sources.get(site_name)
        if not url: return []

        threshold_date = datetime.now() - timedelta(days=days_limit)
        articles = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            
            if resp.status_code != 200:
                return []
            
            xml_data = re.sub(r'\sxmlns="[^"]+"', '', resp.text, count=1)
            root = ET.fromstring(xml_data)

            # 增强兼容性：同时找 RSS的<item> 和 Atom的<entry>
            items = root.findall('.//item')
            if not items:
                items = root.findall('.//entry')

            for item in items:
                title = item.find('title')
                
                # 兼容不同格式的链接
                link_text = ""
                link_node = item.find('link')
                if link_node is not None:
                    link_text = link_node.text if link_node.text else link_node.get('href', '')
                
                # 兼容不同格式的时间标签
                pub_date = item.find('pubDate')
                if pub_date is None: pub_date = item.find('updated')
                if pub_date is None: pub_date = item.find('published')

                article_title = title.text.strip() if title is not None and title.text else "无标题"
                article_link = link_text.strip() if link_text else ""
                article_time_str = pub_date.text.strip() if pub_date is not None and pub_date.text else ""

                # ==========================================
                # 💡 核心修复：超强容错的时间解析逻辑
                # ==========================================
                formatted_time = "未知时间"
                if article_time_str:
                    try:
                        # 暴力切除时间字符串末尾可能导致报错的时区信息（如 +0800, GMT, Z等）
                        clean_time = re.sub(r'\s*[+-]\d{4}$|\s*[a-zA-Z]{1,4}$|Z$', '', article_time_str)
                        
                        # 准备多种常见的时间格式
                        date_formats = [
                            '%a, %d %b %Y %H:%M:%S',
                            '%Y-%m-%dT%H:%M:%S',
                            '%Y-%m-%d %H:%M:%S',
                            '%a, %d %b %Y %H:%M'
                        ]
                        
                        dt = None
                        for fmt in date_formats:
                            try:
                                dt = datetime.strptime(clean_time.strip(), fmt)
                                break # 只要有一种格式试成功了，就跳出循环
                            except ValueError:
                                continue
                        
                        if dt:
                            # 只有真正解析出时间了，才进行天数过滤
                            if dt < threshold_date:
                                continue
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        else:
                            # 所有格式都匹配失败，说明是很奇葩的字符串。
                            # 绝对不扔掉文章，强行保留原始字符串显示！
                            formatted_time = article_time_str[:20]
                            
                    except Exception:
                        pass # 出错不抛弃，继续往下走，用 "未知时间" 显示
                
                articles.append({
                    "title": article_title,
                    "link": article_link,
                    "time": formatted_time,
                    "source": site_name
                })

            return articles
        except Exception as e:
            return []

# ================= 网页 UI 部分 =================
st.title("📱 科技资讯 AI 监控站")
st.markdown("从官网直连获取最新资讯，并由 **DeepSeek 大模型** 自动生成硬核摘要。")

with st.sidebar:
    st.header("⚙️ 监控设置")
    days_to_fetch = st.slider("获取多少天内的文章？", min_value=1, max_value=7, value=1)
    start_btn = st.button("🚀 立即获取并让 AI 总结", type="primary")
    st.markdown("---")
    st.caption("提示：用手机连接电脑同局域网的 WiFi，输入本网页的 Network URL 即可访问。")

monitor = WebMonitor()

if start_btn:
    with st.spinner(f'正在前往官网抓取 {days_to_fetch} 天内的新闻，并呼叫 DeepSeek...'):
        all_articles = []
        for name in monitor.sources.keys():
            all_articles.extend(monitor.fetch_articles(name, days_to_fetch))
        
        # 按时间倒序排列（把带有"未知时间"的放到最后面）
        all_articles.sort(key=lambda x: x['time'] if x['time'] != "未知时间" else "1970", reverse=True)
        
        if not all_articles:
            st.warning("这段时间没有新文章，或者网络开小差了。")
        else:
            st.success(f"共发现 {len(all_articles)} 篇新鲜资讯！")
            
            for art in all_articles:
                with st.container():
                    st.subheader(f"【{art['source']}】{art['title']}")
                    st.caption(f"发布时间: {art['time']}")
                    
                    full_text = monitor.get_article_content(art['link'])
                    summary = monitor.summarize_with_ai(full_text)
                    
                    st.info(f"**🤖 DeepSeek 划重点：**\n\n{summary}")
                    st.markdown(f"[👉 点击这里阅读原文]({art['link']})")
                    st.divider()
