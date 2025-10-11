/* eslint-disable @typescript-eslint/no-explicit-any */

import { Button, Input, Space, Alert } from 'antd';
import { MailOutlined, LeftOutlined } from '@ant-design/icons';
import LoginHeader from './LoginHeader';
import LoginFooter from './LoginFooter';

const EmailOTP = ({ onSendOtp, onBack, email, setEmail, isLoading, error, footerProps }: {
    onSendOtp: () => void;
    onBack: () => void;
    email: string;
    setEmail: (email: string) => void;
    isLoading: boolean;
    error?: string;
    footerProps: any;
}) => (
    <Space direction="vertical" size="large" className="w-full">
        <LoginHeader />
        <Space direction="vertical" size="middle" className="w-full">
            {error && (
                <Alert
                    message="Error"
                    description={error}
                    type="error"
                    showIcon
                    className="mb-4"
                />
            )}
            <Input
                prefix={<MailOutlined className="text-blue-500" />}
                placeholder="Enter your email"
                size="large"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onPressEnter={onSendOtp}
                className="border-blue-300 focus:border-blue-500 hover:border-blue-400"
            />
            <div className="flex w-full gap-3">
                <Button
                    type="primary"
                    size="large"
                    loading={isLoading}
                    onClick={onSendOtp}
                    className="bg-gradient-to-r from-blue-500 to-blue-600 border-none shadow-md hover:shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-blue-700 flex-[3]"
                >
                    Send OTP
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

export default EmailOTP;
