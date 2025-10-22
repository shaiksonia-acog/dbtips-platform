/* eslint-disable @typescript-eslint/no-explicit-any */

import { Button, Input, Space, Alert } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import LoginHeader from './LoginHeader';
import LoginFooter from './LoginFooter';

const OTPVerify = ({ onVerifyOtp, onBack, otp, setOtp, isLoading, error, footerProps }: {
    onVerifyOtp: () => void;
    onBack: () => void;
    otp: string;
    setOtp: (otp: string) => void;
    isLoading: boolean;
    error?: string;
    footerProps: any;
}) => (
    <Space direction="vertical" size="middle" className="w-full">
        <LoginHeader />

        <div className="bg-blue-50 border border-blue-300 text-blue-800 rounded-lg p-3 text-sm">
            <div className="flex items-center">
                <MailOutlined className="mr-2 text-blue-600" />
                OTP sent successfully! Please check your email.
            </div>
        </div>

        {error && (
            <Alert
                message="Verification Failed"
                description={error}
                type="error"
                showIcon
                className="mb-4"
            />
        )}

        <Input
            placeholder="Enter OTP"
            size="large"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            onPressEnter={onVerifyOtp}
            maxLength={6}
            className="text-center text-xl tracking-widest border-blue-300 focus:border-blue-500 hover:border-blue-400"
        />

        <div className="flex w-full gap-3">
            <Button
                type="primary"
                size="large"
                loading={isLoading}
                onClick={onVerifyOtp}
                className="bg-gradient-to-r from-blue-500 to-blue-600 border-none shadow-md hover:shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-blue-700 flex-[3]"
            >
                Verify OTP
            </Button>
            <Button
                size="large"
                onClick={onBack}
                className="border-blue-300 text-blue-600 hover:border-blue-500 hover:text-blue-700 flex-1"
            >
                Change Email
            </Button>
        </div>

        <LoginFooter {...footerProps} />
    </Space>
);

export default OTPVerify;
