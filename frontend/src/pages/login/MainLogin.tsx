
import { Button, Space } from 'antd';
import { MailOutlined, LockOutlined } from '@ant-design/icons';
import LoginHeader from './LoginHeader';
import LoginFooter from './LoginFooter';

const MainLogin = ({ onEmailLogin, onLdapLogin, footerProps }) => (
    <Space direction="vertical" size="large" className="w-full">
        <LoginHeader />
        <Space direction="vertical" size="middle" className="w-full">
            <Button
                type="primary"
                size="large"
                block
                icon={<MailOutlined />}
                onClick={onEmailLogin}
                className="bg-gradient-to-r from-blue-500 to-blue-600 border-none h-12 shadow-md hover:shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-blue-700"
            >
                Login with Email OTP
            </Button>
            <Button
                type="primary"
                size="large"
                block
                icon={<LockOutlined />}
                onClick={onLdapLogin}
                className="bg-gradient-to-r from-blue-600 to-blue-800 border-none h-12 shadow-md hover:shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-blue-900"
            >
                Login with LDAP
            </Button>
        </Space>
        <LoginFooter {...footerProps} />
    </Space>
);

export default MainLogin;
