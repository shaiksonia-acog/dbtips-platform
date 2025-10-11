/* eslint-disable @typescript-eslint/no-explicit-any */

import { Button, Input, Space, Alert } from 'antd';
import { UserOutlined, LockOutlined, LeftOutlined } from '@ant-design/icons';
import LoginHeader from './LoginHeader';
import LoginFooter from './LoginFooter';

const LDAPLogin = ({ onLdapLogin, onBack, username, setUsername, password, setPassword, isLoading, error, footerProps }: {
    onLdapLogin: () => void;
    onBack: () => void;
    username: string;
    setUsername: (username: string) => void;
    password: string;
    setPassword: (password: string) => void;
    isLoading: boolean;
    error?: string;
    footerProps: any;
}) => (
    <Space direction="vertical" size="large" className="w-full">
        <LoginHeader />
        <Space direction="vertical" size="middle" className="w-full">
            {error && (
                <Alert
                    message="Login Failed"
                    description={error}
                    type="error"
                    showIcon
                    className="mb-4"
                />
            )}
            <Input
                prefix={<UserOutlined className="text-blue-500" />}
                placeholder="Username"
                size="large"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="border-blue-300 focus:border-blue-500 hover:border-blue-400"
            />
            <Input.Password
                prefix={<LockOutlined className="text-blue-500" />}
                placeholder="Password"
                size="large"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onPressEnter={onLdapLogin}
                className="border-blue-300 focus:border-blue-500 hover:border-blue-400"
            />
            <div className="flex w-full gap-3">
                <Button
                    type="primary"
                    size="large"
                    loading={isLoading}
                    onClick={onLdapLogin}
                    className="bg-gradient-to-r from-blue-500 to-blue-600 border-none shadow-md hover:shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-blue-700 flex-[3]"
                >
                    Login
                </Button>
                <Button
                    icon={<LeftOutlined />}
                    size="large"
                    onClick={onBack}
                    className="border-blue-300 text-blue-600 hover:border-blue-500 hover:text-blue-700 flex-1"
                >
                    Back
                </Button>
            </div>
        </Space>
        <LoginFooter {...footerProps} />
    </Space>
);

export default LDAPLogin;
