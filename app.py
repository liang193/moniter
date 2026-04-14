import os
# 🌟 杀手锏：强行抹除系统环境变量里的幽灵代理，防止请求卡死
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''

import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from collections import defaultdict

# ================= 配置区 =================
API_KEY = "sk-75ef6c3357db4ce49284f8534b119006"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
# ==========================================

st.set_page_config(page_title="高级 AI 资讯监控站", page_icon="🚀", layout="wide")

class WebMonitor:
    def __init__(self):
        self.sources = {
            "量子位": "https://www.qbitai.com/feed",
            "36氪": "https://36kr.com/feed",
            "极客公园": "https://www.geekpark.net/rss",
            "爱范儿": "https://www.ifanr.com/feed",
            "IT之家": "https://www.ithome.com/rss/"
        }
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.scraper.proxies = {"http": None, "https": None}

    def get_data_with_browser(self, url):
        """🌟 终极必杀技：在已通过验证的浏览器内部直接下载源码，杜绝一切指纹校验"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url)
                
                # 等待 15 秒钟人工打钩验证码（如果没拦截，无非就是多等15秒）
                page.wait_for_timeout(15000) 
                
                # 💡 核心魔法：直接在浏览器控制台执行请求，拿到最纯粹的数据
                raw_text = page.evaluate('''async () => {
                    const response = await fetch(location.href);
                    return await response.text();
                }''')
                
                browser.close()
                return raw_text
        except Exception as e:
            print(f"弹窗获取失败: {e}")
            return None

    def summarize_with_ai(self, content):
        """🌟 任务升级：深度摘要（100字左右）+ 智能分类"""
        if not content.strip() or not API_KEY:
            return "其他", "⚠️ 无法获取正文内容。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        system_prompt = """你是一个专业的科技主编。请对文章进行深度解析并完成：
1. 分类标签：从【新思路】、【新应用】、【趣事新闻】、【行业发展】中选一个。
2. 深度摘要：撰写一段100字左右的摘要。要求涵盖文章的核心技术点、商业影响或独到见解。语言要专业、干练，不要套话。

返回格式必须严格如下（不要带任何额外字符）：
标签：[标签名]
摘要：[深度摘要内容]"""

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"文章内容（截取）：\n{content[:2500]}"}
            ]
        }

        try:
            import requests 
            response = requests.post(API_URL, headers=headers, json=payload, timeout=20, proxies={"http": None, "https": None})
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content']
            
            tag = "其他"
            summary = result_text
            
            for line in result_text.strip().split('\n'):
                if '标签：' in line:
                    tag = line.split('：')[1].strip().replace('[','').replace(']','')
                if '摘要：' in line:
                    summary = line.split('：')[1].strip()
            
            return tag, summary
        except Exception as e:
            return "其他", f"🤖 AI 总结失败: {str(e)}"

    def fetch_articles(self, site_name, days_limit):
        """获取文章并包含浏览器弹窗兜底机制 + 完善的链接提取"""
        url = self.sources.get(site_name)
        if not url: return []

        threshold_date = datetime.now() - timedelta(days=days_limit)
        articles = []

        try:
            # 第一次正常尝试抓取
            resp = self.scraper.get(url, timeout=15)
            resp.encoding = 'utf-8'
            raw_text = resp.text
            
            # 使用 xml 解析器更准确
            soup = BeautifulSoup(raw_text, 'xml')
            items = soup.find_all('item') or soup.find_all('entry')

            # ========================================================
            # 🚨 发现拦截：立刻召唤人工弹窗，并在浏览器内直接获取数据！
            # ========================================================
            if not items or resp.status_code in [403, 503]:
                print(f"⚠️ {site_name} 发起了拦截，正在召唤人工弹窗...")
                raw_text = self.get_data_with_browser(url)
                
                if raw_text:
                    soup = BeautifulSoup(raw_text, 'xml')
                    items = soup.find_all('item') or soup.find_all('entry')

            if not items:
                return [{
                    "title": f"⚠️ {site_name} 数据获取彻底失败",
                    "link": url,
                    "time": "未知时间",
                    "source": site_name,
                    "error_msg": "已尝试弹窗验证，但仍未获取到文章数据。请检查目标网站是否暂时崩溃。"
                }]

            for item in items:
                title_tag = item.find('title')
                article_title = title_tag.get_text(strip=True) if title_tag else "无标题"
                
                # 💡 三级链接提取大法，确保绝对能点开
                article_link = ""
                for link_tag in item.find_all('link'):
                    temp_link = link_tag.get_text(strip=True) or link_tag.get('href', '')
                    if temp_link.startswith('http'):
                        article_link = temp_link
                        break
                
                if not article_link:
                    guid_tag = item.find('guid') or item.find('id')
                    if guid_tag:
                        temp_link = guid_tag.get_text(strip=True)
                        if temp_link.startswith('http'):
                            article_link = temp_link

                pub_tag = item.find('pubDate') or item.find('updated') or item.find('published')
                content_tag = item.find('content:encoded') or item.find('description') or item.find('content')

                # 时间处理
                article_time_str = pub_tag.get_text(strip=True) if pub_tag else ""
                
                # 清洗正文里的杂乱 HTML 标签
                content_html = content_tag.get_text(strip=True) if content_tag else ""
                clean_content = re.sub(r'<[^>]+>', ' ', content_html)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                article_full_text = clean_content[:2500]

                formatted_time = "未知时间"
                if article_time_str:
                    try:
                        clean_time = re.sub(r'\s*[+-]\d{4}$|\s*[a-zA-Z]{1,4}$|Z$', '', article_time_str)
                        date_formats = [
                            '%a, %d %b %Y %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%a, %d %b %Y %H:%M'
                        ]
                        dt = None
                        for fmt in date_formats:
                            try:
                                dt = datetime.strptime(clean_time.strip(), fmt)
                                break
                            except ValueError:
                                continue
                        
                        if dt:
                            if dt < threshold_date:
                                continue
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        else:
                            formatted_time = article_time_str[:20]
                    except Exception:
                        pass
                
                if article_link:
                    articles.append({
                        "title": article_title,
                        "link": article_link,
                        "time": formatted_time,
                        "content": article_full_text,
                        "source": site_name
                    })

            return articles
            
        except Exception as e:
            return [{
                "title": f"⚠️ {site_name} 发生内部错误",
                "link": url,
                "time": "未知时间",
                "source": site_name,
                "error_msg": f"错误详情: {str(e)}"
            }]

# ================= 网页 UI 部分 =================
st.title("📱 科技资讯 AI 监控站")
st.markdown("从官网直连获取最新资讯，并由 **DeepSeek** 自动生成硬核摘要与分类打标。")

with st.sidebar:
    st.header("⚙️ 监控设置")
    
    monitor = WebMonitor()
    available_sources = list(monitor.sources.keys())
    
    # 源选择器
    selected_sources = st.multiselect(
        "选择要监控的源：",
        options=available_sources,
        default=["量子位", "36氪"]
    )
    
    days_to_fetch = st.slider("获取多少天内的文章？", min_value=1, max_value=7, value=1)
    start_btn = st.button("🚀 立即获取并让 AI 总结", type="primary")
    
    st.markdown("---")
    # 预留左侧智能目录的位置
    catalog_area = st.empty()

if start_btn:
    if not selected_sources:
        st.error("请至少选择一个源！")
    else:
        with st.spinner(f'正在获取新闻，若遇到拦截将会自动弹出验证窗口...'):
            all_articles = []
            for name in selected_sources:
                all_articles.extend(monitor.fetch_articles(name, days_to_fetch))
            
            all_articles.sort(key=lambda x: x['time'] if x['time'] != "未知时间" else "1970", reverse=True)
            
            if not all_articles:
                st.warning("这段时间没有新文章，或者网络开小差了。")
            else:
                st.success(f"共发现 {len(all_articles)} 篇新鲜资讯！")
                
                # 初始化目录数据结构
                catalog = defaultdict(lambda: defaultdict(list))
                
                for art in all_articles:
                    with st.container():
                        st.subheader(f"{art['title']}")
                        
                        if "error_msg" in art:
                            st.error(f"**未能正常获取数据：**\n\n{art['error_msg']}")
                            st.markdown(f"[👉 点击测试源链接是否正常]({art['link']})")
                            st.divider()
                            continue
                        
                        # AI 分类与深度总结
                        tag, summary = monitor.summarize_with_ai(art['content'])
                        catalog[art['source']][tag].append(art)
                        
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"📂 **{art['source']}**")
                            st.write(f"🏷️ `{tag}`")
                            st.caption(f"{art['time']}")
                        with col2:
                            st.info(f"**🤖 DeepSeek 深度摘要：**\n\n{summary}")
                            st.markdown(f"[🔗 阅读全文]({art['link']})")
                        st.divider()

                # 渲染左侧智能目录
                with catalog_area.container():
                    st.header("📑 智能目录")
                    for s_name, tags in catalog.items():
                        with st.expander(f"📌 {s_name}", expanded=True):
                            for t_name, arts in tags.items():
                                st.markdown(f"**{t_name}**")
                                for a in arts:
                                    st.markdown(f"- [{a['title']}]({a['link']})")
