import { MenuOutlined } from '@ant-design/icons'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Button, ConfigProvider, Drawer, Layout } from 'antd'
import type { ThemeConfig } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import RecommendPage from './pages/RecommendPage'
import ReportsPage from './pages/ReportsPage'
import BacktestPage from './pages/BacktestPage'
import TalentsPage from './pages/TalentsPage'

const queryClient = new QueryClient()

const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#f07643',
    colorInfo: '#f07643',
    colorSuccess: '#56a97a',
    colorWarning: '#f5a524',
    colorError: '#d9573f',
    colorTextBase: '#3a352d',
    colorBgBase: '#fffaf2',
    colorBgLayout: '#fffaf2',
    colorLink: '#e5682f',
    borderRadius: 14,
    controlHeight: 38,
    fontFamily:
      '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
}

const navItems = [
  { to: '/', label: '智能推荐', end: true },
  { to: '/reports', label: '报告历史', end: false },
  { to: '/backtest', label: '回测校准', end: false },
  { to: '/talents', label: '特长生查询', end: false },
]

function AppNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
        >
          {item.label}
        </NavLink>
      ))}
    </>
  )
}

export default function App() {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <ConfigProvider locale={zhCN} theme={appTheme}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout style={{ minHeight: '100vh' }}>
            <Layout.Header className="site-header">
              <div className="brand">
                <span className="brand-mark" aria-hidden>
                  ☀️
                </span>
                <div className="brand-text">
                  <div className="brand-title">西安中考志愿智能分析</div>
                  <div className="brand-sub">每个小孩都有光明的未来</div>
                </div>
              </div>
              <nav className="site-nav">
                <AppNav />
              </nav>
              <Button
                className="nav-toggle"
                type="text"
                icon={<MenuOutlined />}
                aria-label="打开导航"
                onClick={() => setNavOpen(true)}
              />
            </Layout.Header>

            <Layout.Content className="site-content">
              <section className="page-hero">
                <div className="page-hero-kicker">2026 西安中考 · 志愿参考</div>
                <h1 className="page-hero-title">
                  每个小孩都有<em>光明的未来</em>
                </h1>
                <p className="page-hero-sub">
                  把历年位次、招生计划和你自己的画像放在一起，让志愿填报少一点玄学、多一点底气。
                </p>
                <span className="page-hero-sun" aria-hidden>
                  🌤️
                </span>
              </section>

              <div className="page-wrap">
                <Routes>
                  <Route path="/" element={<RecommendPage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/backtest" element={<BacktestPage />} />
                  <Route path="/talents" element={<TalentsPage />} />
                </Routes>
              </div>
            </Layout.Content>

            <Layout.Footer className="site-footer">
              <span>
                每个小孩都有<span className="heart">光明的未来</span>
              </span>
              <span>数据与建议仅供志愿参考，请以教育部门官方发布为准</span>
            </Layout.Footer>
          </Layout>

          <Drawer
            className="nav-drawer"
            placement="right"
            width={260}
            open={navOpen}
            onClose={() => setNavOpen(false)}
            title="导航"
          >
            <AppNav onNavigate={() => setNavOpen(false)} />
          </Drawer>
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  )
}
