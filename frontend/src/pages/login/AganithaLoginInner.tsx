/* eslint-disable @typescript-eslint/no-unused-vars */
import { useState } from 'react';
import { useMutation } from 'react-query';
import { fetchData } from './utils';
import MainLogin from './MainLogin';
import EmailOTP from './EmailOTP';
import OTPVerify from './OTPVerify';
import LDAPLogin from './LDAPLogin';

// TypeScript interfaces
interface ApiResponse {
    message?: string;
    detail?: string;
}

interface VerifyOtpPayload {
    email: string;
    otp: string;
}

interface LdapLoginPayload {
    username: string;
    password: string;
}

function AganithaLoginInner() {
    const [currentView, setCurrentView] = useState('main');
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const showContact = () => console.log("Contact us clicked");
    const showTerms = () => console.log("Terms of Service clicked");
    const showPrivacy = () => console.log("Privacy Policy clicked");

    const footerProps = {
        onContact: showContact,
        onTerms: showTerms,
        onPrivacy: showPrivacy
    };

    // Send OTP mutation
    const sendOtpMutation = useMutation<ApiResponse, Error, string>(
        (email: string) => fetchData({ email }, '/send-otp/'),
        {
            onSuccess: (data) => {
                console.log("OTP sent:", data?.message || 'Success');
                setCurrentView('otp-verify');
            },
            onError: (error) => {
                console.log("Failed to send OTP:", error.message);
            }
        }
    );

    // Verify OTP mutation
    const verifyOtpMutation = useMutation<ApiResponse, Error, VerifyOtpPayload>(
        ({ email, otp }: VerifyOtpPayload) => fetchData({ email, otp }, '/verify-otp/'),
        {
            onSuccess: (_data) => {
                console.log("Login successful!");
                window.location.href = "/";
            },
            onError: (error) => {
                console.log("Invalid OTP:", error.message);
            }
        }
    );

    // LDAP login mutation
    const ldapLoginMutation = useMutation<Response, Error, LdapLoginPayload>(
        ({ username, password }: LdapLoginPayload) => fetchData({ username, password }, '/ldap-login/'),
        {
            onSuccess: (_data) => {
                console.log("LDAP login successful");
                window.location.href = "/";
            },
            onError: (error) => {
                console.log("LDAP failed:", error.message);
            }
        }
    );

    const sendOtp = () => {
        if (!email) return;
        sendOtpMutation.mutate(email);
    };

    const verifyOtp = () => {
        if (!otp) return;
        verifyOtpMutation.mutate({ email, otp });
    };

    const loginWithLdap = () => {
        if (!username || !password) return;
        ldapLoginMutation.mutate({ username, password });
    };

    const goBack = () => {
        if (currentView === 'otp-verify') {
            setCurrentView('email-otp');
            setOtp('');
            verifyOtpMutation.reset(); // Clear previous error
        } else {
            setCurrentView('main');
            setEmail('');
            setUsername('');
            setPassword('');
            // Reset all mutations
            sendOtpMutation.reset();
            verifyOtpMutation.reset();
            ldapLoginMutation.reset();
        }
    };

    const renderCurrentView = () => {
        switch (currentView) {
            case 'main':
                return <MainLogin onEmailLogin={() => setCurrentView('email-otp')} onLdapLogin={() => setCurrentView('ldap')} footerProps={footerProps} />;
            case 'email-otp':
                return (
                    <EmailOTP
                        onSendOtp={sendOtp}
                        onBack={goBack}
                        email={email}
                        setEmail={setEmail}
                        isLoading={sendOtpMutation.isLoading}
                        error={sendOtpMutation.error?.message}
                        footerProps={footerProps}
                    />
                );
            case 'otp-verify':
                return (
                    <OTPVerify
                        onVerifyOtp={verifyOtp}
                        onBack={goBack}
                        otp={otp}
                        setOtp={setOtp}
                        isLoading={verifyOtpMutation.isLoading}
                        error={verifyOtpMutation.error?.message}
                        footerProps={footerProps}
                    />
                );
            case 'ldap':
                return (
                    <LDAPLogin
                        onLdapLogin={loginWithLdap}
                        onBack={goBack}
                        username={username}
                        setUsername={setUsername}
                        password={password}
                        setPassword={setPassword}
                        isLoading={ldapLoginMutation.isLoading}
                        error={ldapLoginMutation.error?.message}
                        footerProps={footerProps}
                    />
                );
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-400 via-blue-600 to-blue-800 px-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl p-12 border border-blue-100">
                {renderCurrentView()}
            </div>
        </div>
    );
}

export default AganithaLoginInner;
