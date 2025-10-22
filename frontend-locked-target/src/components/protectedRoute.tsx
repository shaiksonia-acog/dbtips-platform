/* eslint-disable @typescript-eslint/no-unused-vars */
import React from "react";
import { Navigate } from "react-router-dom";
import { useQuery } from "react-query";
import LoadingButton from "./loading";

interface Props {
	children: JSX.Element;
}

const fetchSession = async () => {
	const res = await fetch(`${import.meta.env.VITE_API_URI}/me`, {
		credentials: "include", // send cookie
	});

	if (!res.ok) {
		throw new Error("Not authenticated");
	}
	return res.json();
};

const ProtectedRoute: React.FC<Props> = ({ children }) => {
	const { data, isLoading, isError } = useQuery("session", fetchSession, {
		retry: false, // don’t retry if unauthenticated
	});
	console.log("ProtectedRoute data:", data);

	if (isLoading) return <div><LoadingButton/></div>;

	// If error means not authenticated → redirect to login
	if (isError) return <Navigate to="/login" replace />;

	// Otherwise authenticated → render children
	return children;
};

export default ProtectedRoute;
