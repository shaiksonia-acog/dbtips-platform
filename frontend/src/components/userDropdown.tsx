import React from "react";
import { Dropdown,  Button } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { LogOut } from "lucide-react";

interface Props {
  email: string;
  onLogout: () => void;
}

const UserDropdown: React.FC<Props> = ({ email, onLogout }) => {
  const menu = {
    items: [
      {
        key: "email",
        label: email,
        disabled: true,
        icon: <UserOutlined />,
      },
      {
        type: "divider" as const,
      },
      {
        key: "logout",
        label: "Logout",
        onClick: onLogout,
        icon:<LogOut size={16} />
      },
    ],
  };

  return (
    <Dropdown menu={menu} placement="bottomRight" trigger={["click"]}>
      <Button
        type="text"
        style={{ padding: 0 }}
        icon={<UserOutlined style={{ fontSize: '20px', }}  />}
      />
    </Dropdown>
  );
};

export default UserDropdown;
