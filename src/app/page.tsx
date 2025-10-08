import { getServerSession } from "next-auth/next";
import { redirect } from "next/navigation";
export default async function Home() {
  const session = await getServerSession()
    if(!session){
      redirect('/auth')
    }
  return (
    <div>
      <h1>Home</h1>
      {!session ? (
        <div>
          <h2>Please sign in to access the website.</h2>
          </div>
      ) : (
        <div>
          <h2>we present you our website. Mr. {session.user.name}</h2>

        </div>
      )}
    </div>
  );
}
