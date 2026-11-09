import { Alert, Button, Form, Input, Modal, Segmented, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { errorText } from '../api'
import { useAuth } from '../context/AuthContext'

interface FormValues {
  username: string
  password: string
  confirm?: string
  display_name?: string
}

type Mode = 'login' | 'register'

export default function AuthModal() {
  const { loginOpen, closeLogin, login, register } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form] = Form.useForm<FormValues>()

  useEffect(() => {
    if (loginOpen) {
      setError('')
      setLoading(false)
      form.resetFields()
    }
  }, [loginOpen, form])

  const onFinish = async (values: FormValues) => {
    setLoading(true)
    setError('')
    try {
      if (mode === 'login') {
        await login({ username: values.username.trim(), password: values.password })
      } else {
        await register({
          username: values.username.trim(),
          password: values.password,
          display_name: values.display_name?.trim() || undefined,
        })
      }
      closeLogin()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={loginOpen}
      onCancel={closeLogin}
      footer={null}
      width={420}
      title={mode === 'login' ? '登录账号' : '注册新账号'}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Segmented<Mode>
          block
          value={mode}
          onChange={(value) => {
            setMode(value)
            setError('')
            form.resetFields()
          }}
          options={[
            { label: '登录', value: 'login' },
            { label: '注册', value: 'register' },
          ]}
        />
        <Typography.Text type="secondary">
          {mode === 'login'
            ? '登录后可以保存多套志愿方案、做并排对比并生成分享链接。不登录也能照常使用推荐与查询。'
            : '账号只保存在本机数据库中，密码经 PBKDF2 加盐哈希存储，不会保存明文。'}
        </Typography.Text>

        {error && <Alert type="error" showIcon message={error} />}

        <Form<FormValues> form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, max: 30, message: '用户名需 3–30 位' },
            ]}
          >
            <Input autoComplete="username" placeholder="3–30 位字符" />
          </Form.Item>
          {mode === 'register' && (
            <Form.Item label="昵称（可选）" name="display_name">
              <Input placeholder="分享页里展示的称呼" maxLength={30} />
            </Form.Item>
          )}
          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, max: 64, message: '密码至少 6 位' },
            ]}
          >
            <Input.Password
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder="至少 6 位"
            />
          </Form.Item>
          {mode === 'register' && (
            <Form.Item
              label="确认密码"
              name="confirm"
              dependencies={['password']}
              rules={[
                { required: true, message: '请再次输入密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) return Promise.resolve()
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password autoComplete="new-password" placeholder="再输一次" />
            </Form.Item>
          )}
          <Button type="primary" htmlType="submit" block loading={loading} style={{ marginTop: 4 }}>
            {mode === 'login' ? '登录' : '注册并登录'}
          </Button>
        </Form>
      </Space>
    </Modal>
  )
}
